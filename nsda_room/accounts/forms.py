from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class StudentRegistrationForm(UserCreationForm):
    """Registration form for students."""

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password1', 'password2', 'phone', 'grade_level',
            'school', 'date_of_birth', 'profile_picture',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        if commit:
            user.save()
        return user


class TeacherRegistrationForm(UserCreationForm):
    """Registration form for teachers."""

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password1', 'password2', 'phone', 'bio',
            'school', 'profile_picture',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        if commit:
            user.save()
        return user


class AdminRegistrationForm(UserCreationForm):
    """Registration form for admins (used by superusers)."""

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password1', 'password2', 'phone',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.ADMIN
        user.is_staff = True
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile."""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'bio', 'grade_level', 'school', 'date_of_birth',
            'profile_picture',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class CustomLoginForm(AuthenticationForm):
    """Styled login form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'on',
            })
