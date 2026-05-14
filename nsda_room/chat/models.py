from django.db import models
from django.conf import settings


class ChatRoom(models.Model):
    """A chat room for real-time messaging."""

    class RoomType(models.TextChoices):
        DIRECT = 'direct', 'Direct Message'
        GROUP = 'group', 'Group Chat'

    name = models.CharField(max_length=255)
    room_type = models.CharField(
        max_length=10,
        choices=RoomType.choices,
        default=RoomType.DIRECT,
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chat_rooms',
    )
    batch = models.ForeignKey(
        'accounts.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_other_participant(self, user):
        """For direct messages, get the other participant."""
        if self.room_type == self.RoomType.DIRECT:
            return self.participants.exclude(pk=user.pk).first()
        return None


class Message(models.Model):
    """A message in a chat room."""

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
