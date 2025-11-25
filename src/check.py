import requests
import json

# 여기에 본인의 API 키를 따옴표 안에 넣으세요
API_KEY = "AIzaSyAx8ZLAQFoHE86-NUngtngfXH35wGrOvK4"

# 구글한테 "내가 쓸 수 있는 모델 다 보여줘"라고 요청하는 주소
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print("=== [사용 가능한 모델 목록] ===")
        for model in data.get('models', []):
            # 'generateContent' 기능을 지원하는 모델만 출력
            if "generateContent" in model.get('supportedGenerationMethods', []):
                print(f"이름: {model['name']}")
    else:
        print("에러 발생:", response.text)
except Exception as e:
    print("실행 중 오류:", e)