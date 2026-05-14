"""
URL configuration for NSDA Student Portal.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
    path('accounts/', include('accounts.urls')),
    path('debates/', include('debates.urls')),
    path('chat/', include('chat.urls')),
    path('monitoring/', include('monitoring.urls')),
    path('notifications/', include('notifications.urls')),
    path('exams/', include('exams.urls')),
    path('finance/', include('finance.urls')),
    path('attendance/', include('attendance.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
