from django import forms
from .models import Notice, SharedFile, Assignment, AssignmentSubmission


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content', 'target_role', 'is_pinned']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
        }


class FileShareForm(forms.ModelForm):
    class Meta:
        model = SharedFile
        fields = ['title', 'description', 'file', 'shared_with']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'shared_with': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'attached_file', 'due_date', 'max_score']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['file', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }


class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['grade', 'feedback']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 3}),
        }
