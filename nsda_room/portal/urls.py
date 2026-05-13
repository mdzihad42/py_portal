from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Dashboards
    path('', views.DashboardRedirectView.as_view(), name='dashboard'),
    path('dashboard/student/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/teacher/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # Notices
    path('notices/', views.NoticeListView.as_view(), name='notice_list'),
    path('notices/create/', views.NoticeCreateView.as_view(), name='notice_create'),
    path('notices/<int:pk>/', views.NoticeDetailView.as_view(), name='notice_detail'),

    # Files
    path('files/', views.FileListView.as_view(), name='file_list'),
    path('files/upload/', views.FileUploadView.as_view(), name='file_upload'),

    # Assignments
    path('assignments/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('assignments/create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('assignments/<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),
    path('assignments/<int:pk>/submit/', views.AssignmentSubmitView.as_view(), name='assignment_submit'),
    path('submissions/<int:pk>/grade/', views.GradeSubmissionView.as_view(), name='grade_submission'),
]
