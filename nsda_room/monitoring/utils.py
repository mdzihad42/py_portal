from django.utils import timezone
from attendance.models import Attendance
from django.db.models import F

def update_student_attendance(student, active_seconds=0):
    """Update or create daily attendance record for a student."""
    today = timezone.now().date()
    attendance, created = Attendance.objects.get_or_create(
        student=student,
        date=today
    )
    
    if active_seconds > 0:
        attendance.total_active_seconds = F('total_active_seconds') + active_seconds
    
    attendance.status = 'PRESENT'
    attendance.last_seen = timezone.now()
    attendance.save()
    return attendance
