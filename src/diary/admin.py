from django.contrib import admin
from .models import Feed

# Feed 모델을 관리자 페이지에 등록
@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'content_preview', 'user')
    search_fields = ('email', 'content')

    # 글 내용이 길면 앞부분만 잘라서 보여주기
    def content_preview(self, obj):
        return obj.content[:30] + "..." if obj.content else ""
    content_preview.short_description = "글 내용 미리보기"