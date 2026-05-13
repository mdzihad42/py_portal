from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    """Custom user model with role-based access."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    grade_level = models.CharField(max_length=50, blank=True)
    school = models.CharField(max_length=200, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    def get_absolute_url(self):
        return reverse('accounts:profile')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
