from django.utils import timezone
from datetime import timedelta

from .models import ActivityAlert, AppUsage, KeyboardActivity, MonitoringSession


# Apps considered study-related
STUDY_APPS = {
    'chrome', 'firefox', 'edge', 'safari', 'brave',
    'word', 'excel', 'powerpoint', 'notepad', 'vscode',
    'code', 'sublime', 'atom', 'notion', 'onenote',
    'teams', 'zoom', 'meet', 'classroom', 'canvas',
    'acrobat', 'pdf', 'reader',
}


def check_for_alerts(student, keyboard_data=None):
    """Check for anomalous activity and generate alerts."""

    # 1. Check for inactivity (no data for > 20 minutes during active session)
    active_session = MonitoringSession.objects.filter(
        student=student, is_active=True
    ).first()

    if active_session:
        threshold = timezone.now() - timedelta(minutes=20)
        recent_activity = AppUsage.objects.filter(
            student=student,
            start_time__gte=threshold,
        ).exists()

        recent_keyboard = KeyboardActivity.objects.filter(
            student=student,
            timestamp__gte=threshold,
        ).exists()

        if not recent_activity and not recent_keyboard:
            # Check if alert already exists recently
            recent_alert = ActivityAlert.objects.filter(
                student=student,
                alert_type=ActivityAlert.AlertType.INACTIVITY,
                created_at__gte=threshold,
            ).exists()

            if not recent_alert:
                ActivityAlert.objects.create(
                    student=student,
                    alert_type=ActivityAlert.AlertType.INACTIVITY,
                    message=f'{student.username} has been inactive for over 20 minutes during an active monitoring session.',
                )

    # 2. Check for high deletion rate in keyboard activity
    if keyboard_data:
        if keyboard_data.total_keystrokes > 0:
            deletion_rate = keyboard_data.deletion_count / keyboard_data.total_keystrokes
            if deletion_rate > 0.4:  # More than 40% deletions
                ActivityAlert.objects.create(
                    student=student,
                    alert_type=ActivityAlert.AlertType.HIGH_DELETION,
                    message=f'{student.username} has an unusually high deletion rate ({deletion_rate:.0%}) in the last {keyboard_data.interval_minutes} minutes.',
                )

    # 3. Check for non-study apps
    recent_apps = AppUsage.objects.filter(
        student=student,
        start_time__gte=timezone.now() - timedelta(minutes=10),
    )

    for app_usage in recent_apps:
        app_lower = app_usage.app_name.lower()
        is_study = any(study_app in app_lower for study_app in STUDY_APPS)
        if not is_study and not app_usage.is_idle:
            # Check if we already alerted for this app recently
            existing = ActivityAlert.objects.filter(
                student=student,
                alert_type=ActivityAlert.AlertType.UNKNOWN_APP,
                message__icontains=app_usage.app_name,
                created_at__gte=timezone.now() - timedelta(minutes=30),
            ).exists()

            if not existing:
                ActivityAlert.objects.create(
                    student=student,
                    alert_type=ActivityAlert.AlertType.UNKNOWN_APP,
                    message=f'{student.username} is using a non-study application: {app_usage.app_name}',
                )
