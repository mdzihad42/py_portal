from rest_framework import serializers
from .models import Screenshot, AppUsage, KeyboardActivity, MonitoringSession


class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ['id', 'image', 'session', 'captured_at']
        read_only_fields = ['id', 'captured_at']


class AppUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUsage
        fields = [
            'id', 'app_name', 'window_title', 'start_time',
            'end_time', 'duration_seconds', 'is_idle', 'session',
        ]
        read_only_fields = ['id']


class KeyboardActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyboardActivity
        fields = [
            'id', 'typing_duration_seconds', 'total_keystrokes',
            'deletion_count', 'edit_count', 'interval_minutes', 'session',
        ]
        read_only_fields = ['id']


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringSession
        fields = ['id', 'start_time', 'end_time', 'is_active']
        read_only_fields = ['id', 'start_time']
