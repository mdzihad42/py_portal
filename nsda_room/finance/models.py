from django.db import models
from django.conf import settings

class Fine(models.Model):
    """Tracking fines/jorimana for students."""
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fines',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_fines',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.amount} ({'Paid' if self.is_paid else 'Unpaid'})"
