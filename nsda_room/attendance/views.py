from django.shortcuts import render, redirect
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta

from accounts.models import User
from accounts.mixins import TeacherOrAdminRequiredMixin
from .models import Attendance
from exams.models import QuizSubmission
from debates.models import DebateResult

class AttendanceMarkView(TeacherOrAdminRequiredMixin, View):
    template_name = 'attendance/mark_attendance.html'

    def get(self, request):
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        students = User.objects.filter(role=User.Role.STUDENT).order_by('username')
        existing_attendance = Attendance.objects.filter(date=date).values('student_id', 'status', 'remarks')
        
        attendance_dict = {a['student_id']: {'status': a['status'], 'remarks': a['remarks']} for a in existing_attendance}
        
        return render(request, self.template_name, {
            'students': students,
            'date': date,
            'attendance_dict': attendance_dict,
        })

    def post(self, request):
        date_str = request.POST.get('date')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        students = User.objects.filter(role=User.Role.STUDENT)
        for student in students:
            status = request.POST.get(f'status_{student.id}', Attendance.Status.ABSENT)
            remarks = request.POST.get(f'remarks_{student.id}', '')
            
            Attendance.objects.update_or_create(
                student=student,
                date=date,
                defaults={
                    'status': status,
                    'remarks': remarks,
                    'marked_by': request.user
                }
            )
        
        messages.success(request, f"Attendance for {date} updated successfully.")
        return redirect(f"{request.path}?date={date_str}")

class AttendanceReportView(TeacherOrAdminRequiredMixin, ListView):
    model = Attendance
    template_name = 'attendance/attendance_report.html'
    context_object_name = 'attendances'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['students'] = User.objects.filter(role=User.Role.STUDENT).order_by('username')
        
        # Get last 30 days
        today = timezone.now().date()
        ctx['dates'] = [today - timedelta(days=i) for i in range(14)] # Showing last 14 days for brevity
        
        # Create a matrix-like structure for the template
        report_data = []
        for student in ctx['students']:
            student_attendance = []
            for date in ctx['dates']:
                att = Attendance.objects.filter(student=student, date=date).first()
                student_attendance.append({
                    'date': date,
                    'status': att.status if att else 'N/A'
                })
            report_data.append({
                'student': student,
                'data': student_attendance
            })
        ctx['report_data'] = report_data
        return ctx

class PrizeDashboardView(LoginRequiredMixin, View):
    template_name = 'attendance/prize_dashboard.html'

    def get(self, request):
        # Top Performers for the Current Month
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Best Attendance (Count PRESENT)
        top_attendance = User.objects.filter(role=User.Role.STUDENT).annotate(
            present_count=Count('attendances', filter=Q(attendances__status=Attendance.Status.PRESENT, attendances__date__gte=start_of_month))
        ).order_by('-present_count')[:5]

        # 2. Top Exam Marks
        top_exams = User.objects.filter(role=User.Role.STUDENT).annotate(
            total_marks=Sum('quiz_submissions__score', filter=Q(quiz_submissions__submitted_at__gte=start_of_month))
        ).order_by('-total_marks')[:5]

        # 3. Overall Monthly Stars (Simple logic: Combine Rank)
        # For simplicity, we'll just show the top 3 from both
        
        return render(request, self.template_name, {
            'top_attendance': top_attendance,
            'top_exams': top_exams,
            'month': now.strftime('%B %Y')
        })
