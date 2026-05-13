from django.contrib import admin
from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'created_at')
    list_filter = ('room_type',)
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'content_preview', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = 'Content'
