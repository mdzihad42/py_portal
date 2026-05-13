import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat."""

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Check if user is a participant
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message', '').strip()

        if not message_content:
            return

        # Save message to database
        message = await self.save_message(message_content)

        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'sender': self.user.username,
                'sender_id': self.user.id,
                'timestamp': timezone.now().strftime('%H:%M'),
                'sender_name': self.user.get_full_name() or self.user.username,
            }
        )

    async def chat_message(self, event):
        """Send message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def check_participant(self):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            return room.participants.filter(pk=self.user.pk).exists()
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        from .models import ChatRoom, Message
        from notifications.models import Notification
        room = ChatRoom.objects.get(pk=self.room_id)
        msg = Message.objects.create(
            room=room,
            sender=self.user,
            content=content,
        )
        
        # Create notifications for other participants
        for participant in room.participants.exclude(pk=self.user.pk):
            Notification.objects.create(
                user=participant,
                title=f"Message in {room.name}",
                message=f"{self.user.get_full_name() or self.user.username}: {content[:50]}...",
                notification_type=Notification.Type.CHAT,
                link=f"/chat/room/{room.pk}/"
            )
        return msg
