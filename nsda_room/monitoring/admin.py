from django.contrib import admin
from .models import Screenshot, AppUsage, KeyboardActivity, ActivityAlert, MonitoringSession, MonitoringAgentApp

@admin.register(MonitoringSession)
class MonitoringSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'start_time', 'end_time', 'is_active')
    list_filter = ('is_active', 'start_time')

@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ('student', 'captured_at', 'session')
    list_filter = ('captured_at',)

@admin.register(AppUsage)
class AppUsageAdmin(admin.ModelAdmin):
    list_display = ('student', 'app_name', 'window_title', 'duration_seconds', 'is_idle', 'start_time')
    list_filter = ('is_idle', 'start_time')
    search_fields = ('app_name', 'window_title')

@admin.register(KeyboardActivity)
class KeyboardActivityAdmin(admin.ModelAdmin):
    list_display = ('student', 'total_keystrokes', 'deletion_count', 'typing_duration_seconds', 'timestamp')
    list_filter = ('timestamp',)

@admin.register(ActivityAlert)
class ActivityAlertAdmin(admin.ModelAdmin):
    list_display = ('student', 'alert_type', 'message', 'is_reviewed', 'created_at')
    list_filter = ('alert_type', 'is_reviewed', 'created_at')

@admin.register(MonitoringAgentApp)
class MonitoringAgentAppAdmin(admin.ModelAdmin):
    list_display = ('version', 'uploaded_at', 'is_active')
