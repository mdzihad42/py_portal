from django.urls import path
from . import views
from . import api_views

app_name = 'monitoring'

urlpatterns = [
    # Teacher views
    path('', views.MonitoringDashboardView.as_view(), name='dashboard'),
    path('student/<int:student_id>/', views.StudentMonitoringDetailView.as_view(), name='student_detail'),
    path('student/<int:student_id>/screenshots/', views.ScreenshotGalleryView.as_view(), name='screenshots'),
    path('alerts/', views.AlertListView.as_view(), name='alerts'),
    path('alerts/<int:pk>/review/', views.ReviewAlertView.as_view(), name='review_alert'),

    # API endpoints for monitoring agent
    path('api/session/start/', api_views.StartSessionAPI.as_view(), name='api_session_start'),
    path('api/session/<int:session_id>/end/', api_views.EndSessionAPI.as_view(), name='api_session_end'),
    path('api/screenshot/', api_views.ScreenshotUploadAPI.as_view(), name='api_screenshot'),
    path('api/app-usage/', api_views.AppUsageAPI.as_view(), name='api_app_usage'),
    path('api/keyboard/', api_views.KeyboardActivityAPI.as_view(), name='api_keyboard'),
    path('api/check-update/', api_views.CheckUpdateAPI.as_view(), name='api_check_update'),

    # Download monitoring tools
    path('download/agent/', views.DownloadAgentView.as_view(), name='download_agent'),
    path('download/config/', views.DownloadConfigView.as_view(), name='download_config'),
    path('download/setup-package/', views.DownloadPackageView.as_view(), name='download_package'),
]
