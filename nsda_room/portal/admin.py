from django.contrib import admin
from .models import Notice, SharedFile, Assignment, AssignmentSubmission


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'posted_by', 'target_role', 'is_pinned', 'created_at')
    list_filter = ('target_role', 'is_pinned', 'created_at')
    search_fields = ('title', 'content')


@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_by', 'file_type', 'upload_date')
    list_filter = ('file_type', 'upload_date')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'due_date', 'max_score', 'created_at')
    list_filter = ('due_date', 'created_at')


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submitted_at', 'grade', 'is_graded')
    list_filter = ('is_graded', 'submitted_at')
