from django.db import models
from user.models import User

class Feed(models.Model):
    content = models.TextField(blank=True)  # 글내용
    image = models.TextField(blank=True, null=True)  # 피드 이미지
    email = models.EmailField(default='no') 
    
    # User 모델의 user_id 필드와 연결
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feeds', 
                             null=True, blank=True, to_field='user_id')

    def save(self, *args, **kwargs):
        # user_id가 없고 email이 있으면, 자동으로 User를 찾거나 생성해서 연결
        if not self.user_id and self.email:
            # 여기서 User 모델이 정상이어야 에러가 안 납니다.
            self.user, _ = User.objects.get_or_create(email=self.email, defaults={'user_id': self.email.split('@')[0]})
        super().save(*args, **kwargs)

    def __str__(self):
        # user가 있으면 user_id를, 없으면 '익명'을 반환 (에러 방지)
        if self.user:
            return self.user.user_id
        return f"Feed (No User) - {self.pk}"