from django.contrib import admin
from .models import User

# User 모델을 관리자 페이지에 등록
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'user_id', 'name', 'is_admin', 'is_active')
    search_fields = ('email', 'user_id')
    ordering = ('-id',)