from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import MonitoringSession
from .serializers import (
    ScreenshotSerializer, AppUsageSerializer,
    KeyboardActivitySerializer, SessionSerializer,
)
from .alert_engine import check_for_alerts
from .utils import update_student_attendance


class StartSessionAPI(APIView):
    """Start a new monitoring session."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Close any existing active sessions
        MonitoringSession.objects.filter(
            student=request.user, is_active=True
        ).update(is_active=False, end_time=timezone.now())

        session = MonitoringSession.objects.create(student=request.user)
        serializer = SessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EndSessionAPI(APIView):
    """End a monitoring session."""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = MonitoringSession.objects.get(
                pk=session_id, student=request.user
            )
            session.is_active = False
            session.end_time = timezone.now()
            session.save()
            return Response({'status': 'session ended'})
        except MonitoringSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND,
            )


class ScreenshotUploadAPI(APIView):
    """Upload a screenshot from the monitoring agent."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ScreenshotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            update_student_attendance(request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppUsageAPI(APIView):
    """Upload app usage data from the monitoring agent."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Support both single and batch uploads
        data = request.data
        if isinstance(data, list):
            serializer = AppUsageSerializer(data=data, many=True)
        else:
            serializer = AppUsageSerializer(data=data)

        if serializer.is_valid():
            instances = serializer.save(student=request.user)
            # Calculate total duration in this batch
            total_duration = 0
            if isinstance(instances, list):
                total_duration = sum(i.duration_seconds for i in instances if not i.is_idle)
            elif not instances.is_idle:
                total_duration = instances.duration_seconds
            
            update_student_attendance(request.user, active_seconds=total_duration)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KeyboardActivityAPI(APIView):
    """Upload keyboard activity data from the monitoring agent."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = KeyboardActivitySerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(student=request.user)
            # Check for alerts
            check_for_alerts(request.user, keyboard_data=instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
