from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class Batch(models.Model):
    """Educational batch or group (e.g. Batch-1, Batch-2)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Batches"

    def __get_student_count(self):
        return self.students.count()
    student_count = property(__get_student_count)

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom user model with role-based access."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        CR = 'cr', 'Class Representative'
        TEACHER = 'teacher', 'Teacher'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
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
    def is_cr(self):
        return self.role == self.Role.CR

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    @property
    def can_manage_records(self):
        """CR, Teacher, and Admin can manage notices/fines."""
        return self.role in [self.Role.CR, self.Role.TEACHER, self.Role.ADMIN]

    def get_absolute_url(self):
        return reverse('accounts:profile')

    def __str__(self):
        batch_info = f" [{self.batch.name}]" if self.batch else ""
        return f"{self.get_full_name() or self.username} ({self.get_role_display()}){batch_info}"
