from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import UpdateView, ListView
from django.urls import reverse_lazy
from django.contrib import messages

from .forms import (
    StudentRegistrationForm, TeacherRegistrationForm,
    ProfileUpdateForm, CustomLoginForm,
)
from .models import User
from .mixins import AdminRequiredMixin


class RegisterView(View):
    """Handle user registration with role selection."""

    def get(self, request):
        role = request.GET.get('role', 'student')
        form = self._get_form(role)
        return render(request, 'accounts/register.html', {
            'form': form,
            'role': role,
        })

    def post(self, request):
        role = request.POST.get('role', 'student')
        form = self._get_form(role, data=request.POST, files=request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to NSDA Portal, {user.first_name}!')
            return redirect('portal:dashboard')
        return render(request, 'accounts/register.html', {
            'form': form,
            'role': role,
        })

    def _get_form(self, role, **kwargs):
        if role == 'teacher':
            return TeacherRegistrationForm(**kwargs)
        return StudentRegistrationForm(**kwargs)


class LoginView(View):
    """Handle user login."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('portal:dashboard')
        form = CustomLoginForm()
        return render(request, 'accounts/login.html', {'form': form})

    def post(self, request):
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'portal:dashboard')
            return redirect(next_url)
        return render(request, 'accounts/login.html', {'form': form})


class LogoutView(View):
    """Handle user logout."""

    def post(self, request):
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('accounts:login')

    def get(self, request):
        logout(request)
        return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, View):
    """Display user profile."""

    def get(self, request):
        return render(request, 'accounts/profile.html', {
            'profile_user': request.user,
        })


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update user profile."""
    model = User
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


class UserListView(AdminRequiredMixin, ListView):
    """Admin view: list all users."""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('-date_joined')
        role_filter = self.request.GET.get('role')
        if role_filter:
            qs = qs.filter(role=role_filter)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                models.Q(username__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['role_filter'] = self.request.GET.get('role', '')
        ctx['search_query'] = self.request.GET.get('q', '')
        return ctx
