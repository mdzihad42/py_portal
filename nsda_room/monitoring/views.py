from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView
from django.db.models import Sum, Avg, Count, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from accounts.mixins import TeacherOrAdminRequiredMixin
from .models import (
    Screenshot, AppUsage, KeyboardActivity,
    ActivityAlert, MonitoringSession,
)


class MonitoringDashboardView(TeacherOrAdminRequiredMixin, View):
    """Main monitoring dashboard for teachers."""

    def get(self, request):
        students = User.objects.filter(role='student').order_by('first_name', 'username')

        # Active sessions
        active_sessions = MonitoringSession.objects.filter(
            is_active=True
        ).select_related('student')

        # Recent alerts
        recent_alerts = ActivityAlert.objects.filter(
            is_reviewed=False
        ).select_related('student')[:10]

        # Stats
        today = timezone.now().date()
        today_screenshots = Screenshot.objects.filter(
            captured_at__date=today
        ).count()

        today_active_students = MonitoringSession.objects.filter(
            start_time__date=today
        ).values('student').distinct().count()

        # App usage summary for today
        top_apps = AppUsage.objects.filter(
            start_time__date=today, is_idle=False
        ).values('app_name').annotate(
            total_duration=Sum('duration_seconds'),
            user_count=Count('student', distinct=True),
        ).order_by('-total_duration')[:10]

        context = {
            'students': students,
            'active_sessions': active_sessions,
            'recent_alerts': recent_alerts,
            'today_screenshots': today_screenshots,
            'today_active_students': today_active_students,
            'top_apps': top_apps,
            'unreviewed_alerts_count': ActivityAlert.objects.filter(is_reviewed=False).count(),
        }
        return render(request, 'monitoring/dashboard.html', context)


class StudentMonitoringDetailView(TeacherOrAdminRequiredMixin, View):
    """Detailed monitoring view for a specific student."""

    def get(self, request, student_id):
        student = get_object_or_404(User, pk=student_id, role='student')
        days = int(request.GET.get('days', 7))
        since = timezone.now() - timedelta(days=days)

        # Screenshots
        screenshots = Screenshot.objects.filter(
            student=student, captured_at__gte=since
        )[:20]

        # App usage breakdown
        app_usage = AppUsage.objects.filter(
            student=student, start_time__gte=since, is_idle=False
        ).values('app_name').annotate(
            total_duration=Sum('duration_seconds'),
        ).order_by('-total_duration')[:15]

        # Total active vs idle time
        total_active = AppUsage.objects.filter(
            student=student, start_time__gte=since, is_idle=False
        ).aggregate(total=Sum('duration_seconds'))['total'] or 0

        total_idle = AppUsage.objects.filter(
            student=student, start_time__gte=since, is_idle=True
        ).aggregate(total=Sum('duration_seconds'))['total'] or 0

        # Keyboard activity over time
        keyboard_data = KeyboardActivity.objects.filter(
            student=student, timestamp__gte=since
        ).annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            total_keys=Sum('total_keystrokes'),
            total_deletions=Sum('deletion_count'),
            total_typing=Sum('typing_duration_seconds'),
        ).order_by('date')

        # Daily activity (sessions per day)
        daily_sessions = MonitoringSession.objects.filter(
            student=student, start_time__gte=since
        ).annotate(
            date=TruncDate('start_time')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        # Alerts
        alerts = ActivityAlert.objects.filter(
            student=student, created_at__gte=since
        )[:20]

        context = {
            'student': student,
            'screenshots': screenshots,
            'app_usage': app_usage,
            'total_active_minutes': total_active // 60,
            'total_idle_minutes': total_idle // 60,
            'keyboard_data': list(keyboard_data),
            'daily_sessions': list(daily_sessions),
            'alerts': alerts,
            'days': days,
            'app_labels': [a['app_name'] for a in app_usage],
            'app_durations': [a['total_duration'] // 60 for a in app_usage],
        }
        return render(request, 'monitoring/student_detail.html', context)


class ScreenshotGalleryView(TeacherOrAdminRequiredMixin, ListView):
    """Paginated screenshot gallery for a student."""
    model = Screenshot
    template_name = 'monitoring/screenshot_gallery.html'
    context_object_name = 'screenshots'
    paginate_by = 20

    def get_queryset(self):
        student_id = self.kwargs['student_id']
        return Screenshot.objects.filter(
            student_id=student_id
        ).order_by('-captured_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['student'] = get_object_or_404(User, pk=self.kwargs['student_id'])
        return ctx


class AlertListView(TeacherOrAdminRequiredMixin, ListView):
    """List all activity alerts."""
    model = ActivityAlert
    template_name = 'monitoring/alerts.html'
    context_object_name = 'alerts'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('student')
        filter_type = self.request.GET.get('type')
        if filter_type:
            qs = qs.filter(alert_type=filter_type)
        reviewed = self.request.GET.get('reviewed')
        if reviewed == 'false':
            qs = qs.filter(is_reviewed=False)
        return qs


class ReviewAlertView(TeacherOrAdminRequiredMixin, View):
    """Mark an alert as reviewed."""

    def post(self, request, pk):
        alert = get_object_or_404(ActivityAlert, pk=pk)
        alert.is_reviewed = True
        alert.reviewed_by = request.user
        alert.save()
        from django.shortcuts import redirect
        return redirect('monitoring:alerts')
