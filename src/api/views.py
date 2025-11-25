from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.sessions.backends.db import SessionStore
import requests  # [변경] 구글 라이브러리 대신 requests 사용
import json      # [변경] 데이터 포장용
import threading
import time
import os
import uuid
from rest_framework.response import Response
from rest_framework.views import APIView
from uuid import uuid4
from chat.settings import MEDIA_ROOT
import environ

# 환경변수 설정
env = environ.Env(DEBUG=(bool, False))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, '.env')

# 2. .env 파일 읽기
# if os.path.exists(env_path):
#     environ.Env.read_env(env_path)
#     print(f"DEBUG: .env 파일을 찾았습니다! 위치: {env_path}")
# else:
#     print(f"DEBUG: .env 파일을 못 찾겠습니다... 경로 확인 필요: {env_path}")
 
# API 키 가져오기
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()

# 디버깅용: 키 앞뒤에 괄호[]를 쳐보면 공백이 있는지 바로 알 수 있습니다.
# print(f"DEBUG: 적용된 키 -> [{GOOGLE_API_KEY[:5]}...]")

def index(request):
    return redirect('home')

# [핵심 변경] 라이브러리 없이 직접 통신하는 함수
def generate_response(request, session_messages, temperature):
    try:
        # 1. 모델 주소 (아까 성공한 gemini-2.5-flash)
        # 주의: 키는 하드코딩된 상태 유지 (테스트 후 나중에 .env로 변경)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"
        
        # 2. 대화 기록 변환
        gemini_contents = []
        for msg in session_messages:
            role = "user" if msg["role"] == "user" else "model"
            text_content = msg["content"]
            gemini_contents.append({
                "role": role,
                "parts": [{"text": text_content}]
            })

        # 3. 데이터 포장 (안전 설정 추가!)
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 8192,
            },
            # [핵심] 안전 필터 끄기 (BLOCK_NONE)
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }
        
        headers = {'Content-Type': 'application/json'}

        # 4. 요청 보내기
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # 5. 결과 처리
        if response.status_code == 200:
            result = response.json()
            
            # [디버깅] 구글이 뭐라고 했는지 눈으로 확인
            # print("DEBUG: 구글 응답 전체 ->", result) 

            # 답변 추출 시도
            try:
                answer_text = result['candidates'][0]['content']['parts'][0]['text']
                print('Gemini response:', answer_text)

                request.session['messages'].append({
                    "role": "assistant", 
                    "content": answer_text,
                    "id": str(uuid.uuid4())
                })
            except (KeyError, IndexError):
                # 답변이 없을 때 (주로 안전 필터 문제)
                print("DEBUG: 답변 추출 실패. 응답 내용:", result)
                fallback_msg = "죄송해요, 그 질문에는 대답하기가 곤란해요. (안전 필터 또는 구조 오류)"
                
                # 안전 필터에 걸렸는지 확인
                if result.get('candidates') and result['candidates'][0].get('finishReason') == 'SAFETY':
                     fallback_msg = "그 대화 주제는 조금 부끄러워서 대답하기 어려워요. (안전 필터 작동)"

                request.session['messages'].append({
                    "role": "assistant", 
                    "content": fallback_msg,
                    "id": str(uuid.uuid4())
                })

        else:
            print("API Error:", response.text)
            request.session['messages'].append({
                "role": "assistant", 
                "content": f"오류가 났어요. (상태 코드: {response.status_code})",
                "id": str(uuid.uuid4())
            })

        request.session.modified = True

    except Exception as e:
        print(f"Failed to generate response: {e}")
        request.session['messages'].append(
            {"role": "assistant", "content": "죄송해요, 내부 오류가 발생했습니다."})
        request.session.modified = True

# ------------------------------------------------------------------
# 아래 home, new_chat, error_handler, choose_mbti, mbti_chatbot 함수들은 
# 아까 작성하신 것과 동일하게 유지하시면 됩니다. (변경 없음)
# ------------------------------------------------------------------

def home(request):
    try:
        if 'messages' not in request.session:
            request.session['messages'] = []
        
        if request.method == 'POST':
            user_input = request.POST.get('prompt')
            temperature = float(request.POST.get('temperature', 0.1))
            
            # 시스템 프롬프트 추가 로직
            has_system = any(msg.get('display') == False for msg in request.session['messages'])
            if not has_system:
                request.session['messages'].append({
                    "role": "user", 
                    "content": "너는 연애 경험도 많고 연애 고수야. 연애 상담을 해줄 때 친근한 말투로 대답해줘.", 
                    "display": False
                })

            request.session['messages'].append({"role": "user", "content": user_input})
            request.session.modified = True

            response_thread = threading.Thread(
                target=generate_response,
                args=(request, request.session['messages'], temperature)
            )
            response_thread.start()
            response_thread.join(timeout=60)
            
            max_messages = 10
            if len(request.session['messages']) > max_messages:
                request.session['messages'] = request.session['messages'][-max_messages:]

        displayed_messages = [
            message for message in request.session['messages'] if message.get('display', True)
        ]
        context = {
            'messages': displayed_messages,
            'prompt': '',
            'temperature': 0.1,
        }
        return render(request, 'chat/home1.html', context)

    except Exception as e:
        print("에러:", e)
        return redirect('error_handler')


def new_chat(request):
    request.session.pop('messages', None)
    request.session.pop('prompt_added', None) 
    return redirect('home')


def error_handler(request):
    return render(request, 'chat/404.html')


def choose_mbti(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '')
        return redirect('mbti_chatbot', prompt=prompt)
    return render(request, 'chat/choose_mbti.html')


def mbti_chatbot(request, prompt):
    try:
        if 'messages' not in request.session:
            request.session['messages'] = []
        
        if request.method == 'POST':   
            user_input_msg = request.POST.get('prompt') 
            temperature = float(request.POST.get('temperature', 0.1))
            
            if 'prompt_added' not in request.session:
                request.session['messages'].append({
                    "role": "user",
                    "content": f"너는 MBTI에 대해 아주 잘 알고 있는 친구야. 너는 MBTI가 {prompt}인 사람에게 맞춰서 상담해주고 있어. 친근하게 대답해줘.",
                    "display": False
                })
                request.session['prompt_added'] = True

            request.session['messages'].append({"role": "user", "content": user_input_msg})
            request.session.modified = True

            response_thread = threading.Thread(
                target=generate_response,
                args=(request, request.session['messages'], temperature)
            )
            response_thread.start()
            response_thread.join(timeout=60)

            max_messages = 10
            if len(request.session['messages']) > max_messages:
                request.session['messages'] = request.session['messages'][-max_messages:]

            displayed_messages = [
                message for message in request.session['messages'] if message.get('display', True)
            ]
            context = {
                'messages': displayed_messages,
                'prompt': '', 
                'temperature': 0.1,
            }
            return render(request, 'chat/mbti_chatbot.html', context)

        else:
            displayed_messages = [
                message for message in request.session['messages'] if message.get('display', True)
            ]
            context = {
                'messages': displayed_messages,
                'prompt': '',
                'temperature': 0.1,
            }
            return render(request, 'chat/mbti_chatbot.html', context)

    except Exception as e:
        print("MBTI 챗봇 에러:", e)
        return redirect('error_handler')