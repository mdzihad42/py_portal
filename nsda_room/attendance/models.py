from django.db import models
from django.conf import settings
from django.utils import timezone

class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='marked_attendances'
    )
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'date')
        verbose_name_plural = "Attendances"

    def __str__(self):
        return f"{self.student.username} - {self.date} - {self.status}"
