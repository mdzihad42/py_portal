from django.db import models
from django.conf import settings


class Notification(models.Model):
    """User notification."""

    class Type(models.TextChoices):
        DEBATE = 'debate', 'Debate'
        ASSIGNMENT = 'assignment', 'Assignment'
        CHAT = 'chat', 'Chat'
        RESULT = 'result', 'Result'
        NOTICE = 'notice', 'Notice'
        SYSTEM = 'system', 'System'
        MONITORING = 'monitoring', 'Monitoring Alert'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM,
    )
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.title}"
