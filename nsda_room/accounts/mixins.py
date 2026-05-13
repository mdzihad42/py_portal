from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Base mixin for role-based access control."""
    required_role = None

    def test_func(self):
        if self.required_role is None:
            return True
        return self.request.user.role == self.required_role

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('accounts:login')
        return redirect('portal:dashboard')


class StudentRequiredMixin(RoleRequiredMixin):
    required_role = 'student'


class TeacherRequiredMixin(RoleRequiredMixin):
    required_role = 'teacher'


class AdminRequiredMixin(RoleRequiredMixin):
    required_role = 'admin'


class TeacherOrAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow both teachers and admins."""

    def test_func(self):
        return self.request.user.role in ('teacher', 'admin')

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('accounts:login')
        return redirect('portal:dashboard')
