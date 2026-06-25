from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('type', 'title', 'receiver', 'actor', 'is_read', 'created_at', 'read_at')
    list_filter = ('type', 'is_read', 'created_at', 'read_at')
    search_fields = ('title', 'message', 'receiver__email', 'receiver__nickname', 'actor__email', 'actor__nickname')
    raw_id_fields = ('receiver', 'actor', 'recipe', 'comment')
    readonly_fields = ('created_at',)
