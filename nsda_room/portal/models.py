from django.db import models
from django.conf import settings


class Notice(models.Model):
    """Announcements posted by teachers or admins."""

    title = models.CharField(max_length=255)
    content = models.TextField()
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_notices',
    )
    target_role = models.CharField(
        max_length=10,
        choices=[('all', 'All'), ('student', 'Students'), ('teacher', 'Teachers')],
        default='all',
    )
    target_batch = models.ForeignKey(
        'accounts.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notices'
    )
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class SharedFile(models.Model):
    """Files shared between users."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='shared_files/%Y/%m/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_files',
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='received_files',
    )
    file_type = models.CharField(max_length=50, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file and not self.file_type:
            self.file_type = self.file.name.split('.')[-1].upper() if '.' in self.file.name else 'FILE'
        super().save(*args, **kwargs)


class Assignment(models.Model):
    """Assignments created by teachers."""

    title = models.CharField(max_length=255)
    description = models.TextField()
    attached_file = models.FileField(upload_to='assignments/%Y/%m/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_assignments',
    )
    target_batch = models.ForeignKey(
        'accounts.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments'
    )
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    max_score = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return self.title


class AssignmentSubmission(models.Model):
    """Student submissions for assignments."""

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    file = models.FileField(upload_to='submissions/%Y/%m/')
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.PositiveIntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True)
    is_graded = models.BooleanField(default=False)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['assignment', 'student']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"
