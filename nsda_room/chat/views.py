from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView
from django.contrib import messages
from django.db.models import Q, Max

from accounts.models import User
from .models import ChatRoom, Message


class ChatRoomListView(LoginRequiredMixin, ListView):
    """List all chat rooms for the current user."""
    model = ChatRoom
    template_name = 'chat/room_list.html'
    context_object_name = 'rooms'

    def get_queryset(self):
        return ChatRoom.objects.filter(
            participants=self.request.user
        ).annotate(
            last_message_time=Max('messages__timestamp')
        ).order_by('-last_message_time')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['available_users'] = User.objects.exclude(
            pk=self.request.user.pk
        ).order_by('first_name', 'username')
        return ctx


class ChatRoomView(LoginRequiredMixin, View):
    """Display chat room with messages."""

    def get(self, request, pk):
        room = get_object_or_404(ChatRoom, pk=pk)

        if not room.participants.filter(pk=request.user.pk).exists():
            messages.error(request, 'You are not a participant in this room.')
            return redirect('chat:room_list')

        # Mark messages as read
        Message.objects.filter(
            room=room, is_read=False
        ).exclude(sender=request.user).update(is_read=True)

        chat_messages = room.messages.select_related('sender').order_by('timestamp')[:100]

        return render(request, 'chat/chat_room.html', {
            'room': room,
            'chat_messages': chat_messages,
            'other_user': room.get_other_participant(request.user),
        })


class CreateChatRoomView(LoginRequiredMixin, View):
    """Create a new chat room (direct or group)."""

    def post(self, request):
        user_ids = request.POST.getlist('participants')
        room_name = request.POST.get('room_name', '').strip()

        if not user_ids:
            messages.error(request, 'Please select at least one participant.')
            return redirect('chat:room_list')

        if len(user_ids) == 1:
            # Direct message - check if room already exists
            other_user = get_object_or_404(User, pk=user_ids[0])
            existing = ChatRoom.objects.filter(
                room_type='direct',
                participants=request.user,
            ).filter(
                participants=other_user,
            ).first()

            if existing:
                return redirect('chat:room', pk=existing.pk)

            room = ChatRoom.objects.create(
                name=room_name or f'{request.user.username} & {other_user.username}',
                room_type='direct',
            )
            room.participants.add(request.user, other_user)
        else:
            # Group chat
            room = ChatRoom.objects.create(
                name=room_name or 'Group Chat',
                room_type='group',
            )
            room.participants.add(request.user, *user_ids)

        messages.success(request, 'Chat room created!')
        return redirect('chat:room', pk=room.pk)
