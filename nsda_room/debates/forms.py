from django import forms
from .models import Debate, DebateRegistration, DebateResult


class DebateForm(forms.ModelForm):
    class Meta:
        model = Debate
        fields = [
            'title', 'description', 'format', 'topic',
            'date', 'time', 'location', 'status', 'max_participants',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'topic': forms.Textarea(attrs={'rows': 3}),
        }


class DebateRegistrationForm(forms.ModelForm):
    class Meta:
        model = DebateRegistration
        fields = ['team', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class ResultForm(forms.ModelForm):
    class Meta:
        model = DebateResult
        fields = ['score', 'rank', 'feedback']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 3}),
        }
