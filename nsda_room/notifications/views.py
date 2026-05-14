from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkReadView(LoginRequiredMixin, View):
    """Mark a single notification as read and redirect."""

    def get(self, request, pk):
        notification = Notification.objects.filter(
            pk=pk, user=request.user
        ).first()
        if notification:
            notification.is_read = True
            notification.save()
            if notification.link:
                return redirect(notification.link)
        return redirect('notifications:list')

    def post(self, request, pk):
        return self.get(request, pk)


class MarkAllReadView(LoginRequiredMixin, View):
    """Mark all notifications as read."""

    def post(self, request):
        Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return redirect('notifications:list')
