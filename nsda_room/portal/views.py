from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum

from accounts.mixins import (
    StudentRequiredMixin, TeacherRequiredMixin,
    AdminRequiredMixin, TeacherOrAdminRequiredMixin,
    StaffOrCRRequiredMixin,
)
from accounts.models import User
from .models import Notice, SharedFile, Assignment, AssignmentSubmission
from .forms import (
    NoticeForm, FileShareForm, AssignmentForm,
    SubmissionForm, GradeSubmissionForm,
)


# ─── Leaderboard View ────────────────────────────────────────

class LeaderboardView(ListView):
    template_name = 'portal/leaderboard.html'
    context_object_name = 'leaderboard'
    
    def get_queryset(self):
        from monitoring.models import AppUsage
        from exams.models import QuizSubmission
        from debates.models import DebateResult
        
        students = User.objects.filter(role='student')
        leaderboard_data = []
        
        for student in students:
            # 1. Exam Points
            exam_points = QuizSubmission.objects.filter(
                student=student, is_completed=True
            ).aggregate(total=Sum('score'))['total'] or 0
            
            # 2. Attendance Points (10 pts per hour of active monitoring)
            active_seconds = AppUsage.objects.filter(
                student=student, is_idle=False
            ).aggregate(total=Sum('duration_seconds'))['total'] or 0
            attendance_points = (active_seconds // 3600) * 10
            
            # 3. Debate Points
            debate_points = DebateResult.objects.filter(
                student=student
            ).aggregate(total=Sum('score'))['total'] or 0
            
            total_points = float(exam_points) + float(attendance_points) + float(debate_points)
            
            leaderboard_data.append({
                'user': student,
                'exam_points': exam_points,
                'attendance_points': attendance_points,
                'debate_points': float(debate_points),
                'total_points': total_points
            })
        
        return sorted(leaderboard_data, key=lambda x: x['total_points'], reverse=True)


# ─── Dashboard Views ─────────────────────────────────────────

class DashboardRedirectView(LoginRequiredMixin, View):
    """Redirect to role-specific dashboard."""

    def get(self, request):
        if request.user.is_admin_user:
            return redirect('portal:admin_dashboard')
        elif request.user.is_teacher:
            return redirect('portal:teacher_dashboard')
        else:
            return redirect('portal:student_dashboard')


class StudentDashboardView(StudentRequiredMixin, View):
    """Student dashboard with overview."""

    def get(self, request):
        from debates.models import DebateRegistration, DebateResult

        my_debates = DebateRegistration.objects.filter(
            student=request.user
        ).select_related('debate')[:5]

        my_results = DebateResult.objects.filter(
            student=request.user
        ).select_related('debate').order_by('-created_at')[:5]

        pending_assignments = Assignment.objects.filter(
            due_date__gte=timezone.now()
        ).exclude(
            submissions__student=request.user
        )[:5]

        notices = Notice.objects.filter(
            Q(target_role='all') | Q(target_role='student')
        )[:5]

        from monitoring.models import Attendance
        from finance.models import Fine

        total_active_seconds = Attendance.objects.filter(
            student=request.user
        ).aggregate(total=Sum('total_active_seconds'))['total'] or 0
        
        unpaid_fines = Fine.objects.filter(
            student=request.user, is_paid=False
        ).aggregate(total=Sum('amount'))['total'] or 0

        context = {
            'my_debates': my_debates,
            'my_results': my_results,
            'pending_assignments': pending_assignments,
            'notices': notices,
            'total_debates': DebateRegistration.objects.filter(student=request.user).count(),
            'avg_score': DebateResult.objects.filter(student=request.user).aggregate(
                avg=Avg('score')
            )['avg'] or 0,
            'total_active_hours': round(total_active_seconds / 3600, 1),
            'unpaid_fines': unpaid_fines,
        }
        return render(request, 'portal/student_dashboard.html', context)


class TeacherDashboardView(TeacherRequiredMixin, View):
    """Teacher dashboard with analytics."""

    def get(self, request):
        from debates.models import Debate, DebateResult

        context = {
            'total_students': User.objects.filter(role='student').count(),
            'total_debates': Debate.objects.filter(created_by=request.user).count(),
            'recent_debates': Debate.objects.filter(created_by=request.user).order_by('-date')[:5],
            'pending_submissions': AssignmentSubmission.objects.filter(
                assignment__created_by=request.user,
                is_graded=False,
            ).count(),
            'recent_notices': Notice.objects.filter(posted_by=request.user)[:5],
            'recent_submissions': AssignmentSubmission.objects.filter(
                assignment__created_by=request.user,
            ).select_related('student', 'assignment').order_by('-submitted_at')[:5],
        }
        return render(request, 'portal/teacher_dashboard.html', context)


class AdminDashboardView(AdminRequiredMixin, View):
    """Admin dashboard with system overview."""

    def get(self, request):
        from debates.models import Debate

        context = {
            'total_users': User.objects.count(),
            'total_students': User.objects.filter(role='student').count(),
            'total_teachers': User.objects.filter(role='teacher').count(),
            'total_debates': Debate.objects.count(),
            'total_assignments': Assignment.objects.count(),
            'total_notices': Notice.objects.count(),
            'recent_users': User.objects.order_by('-date_joined')[:10],
            'recent_debates': Debate.objects.order_by('-created_at')[:5],
        }
        return render(request, 'portal/admin_dashboard.html', context)


# ─── Notice Views ────────────────────────────────────────────

class NoticeListView(LoginRequiredMixin, ListView):
    model = Notice
    template_name = 'portal/notice_list.html'
    context_object_name = 'notices'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_student:
            qs = qs.filter(Q(target_role='all') | Q(target_role='student'))
        elif self.request.user.is_teacher:
            qs = qs.filter(Q(target_role='all') | Q(target_role='teacher'))
        return qs


class NoticeCreateView(StaffOrCRRequiredMixin, CreateView):
    model = Notice
    form_class = NoticeForm
    template_name = 'portal/notice_form.html'
    success_url = reverse_lazy('portal:notice_list')

    def form_valid(self, form):
        form.instance.posted_by = self.request.user
        messages.success(self.request, 'Notice posted successfully!')
        return super().form_valid(form)


class NoticeDetailView(LoginRequiredMixin, DetailView):
    model = Notice
    template_name = 'portal/notice_detail.html'
    context_object_name = 'notice'


# ─── File Sharing Views ─────────────────────────────────────

class FileListView(LoginRequiredMixin, ListView):
    model = SharedFile
    template_name = 'portal/file_list.html'
    context_object_name = 'files'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        return SharedFile.objects.filter(
            Q(uploaded_by=user) | Q(shared_with=user)
        ).distinct()


class FileUploadView(LoginRequiredMixin, CreateView):
    model = SharedFile
    form_class = FileShareForm
    template_name = 'portal/file_upload.html'
    success_url = reverse_lazy('portal:file_list')

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['shared_with'].queryset = User.objects.exclude(pk=self.request.user.pk)
        return form

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        messages.success(self.request, 'File uploaded successfully!')
        return super().form_valid(form)


# ─── Assignment Views ───────────────────────────────────────

class AssignmentListView(LoginRequiredMixin, ListView):
    model = Assignment
    template_name = 'portal/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.is_teacher:
            return Assignment.objects.filter(created_by=self.request.user)
        return Assignment.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_student:
            submitted_ids = AssignmentSubmission.objects.filter(
                student=self.request.user
            ).values_list('assignment_id', flat=True)
            ctx['submitted_ids'] = set(submitted_ids)
        return ctx


class AssignmentCreateView(TeacherOrAdminRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'portal/assignment_form.html'
    success_url = reverse_lazy('portal:assignment_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Assignment created successfully!')
        return super().form_valid(form)


class AssignmentDetailView(LoginRequiredMixin, DetailView):
    model = Assignment
    template_name = 'portal/assignment_detail.html'
    context_object_name = 'assignment'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_student:
            ctx['submission'] = AssignmentSubmission.objects.filter(
                assignment=self.object,
                student=self.request.user,
            ).first()
            ctx['submit_form'] = SubmissionForm()
        elif self.request.user.is_teacher or self.request.user.is_admin_user:
            ctx['submissions'] = self.object.submissions.select_related('student').all()
            ctx['grade_form'] = GradeSubmissionForm()
        return ctx


class AssignmentSubmitView(StudentRequiredMixin, View):
    """Handle student assignment submission."""

    def post(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        existing = AssignmentSubmission.objects.filter(
            assignment=assignment, student=request.user
        ).first()
        if existing:
            messages.warning(request, 'You have already submitted this assignment.')
            return redirect('portal:assignment_detail', pk=pk)

        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.save()
            messages.success(request, 'Assignment submitted successfully!')
        else:
            messages.error(request, 'Error submitting assignment. Please try again.')
        return redirect('portal:assignment_detail', pk=pk)


class GradeSubmissionView(TeacherOrAdminRequiredMixin, View):
    """Handle teacher grading of submissions."""

    def post(self, request, pk):
        submission = get_object_or_404(AssignmentSubmission, pk=pk)
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.is_graded = True
            sub.save()
            messages.success(request, f'Graded {submission.student.username}\'s submission.')
        return redirect('portal:assignment_detail', pk=submission.assignment.pk)
