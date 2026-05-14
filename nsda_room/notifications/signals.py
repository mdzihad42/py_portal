from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.urls import reverse

from accounts.models import User
from .models import Notification
from portal.models import Notice, Assignment, SharedFile
from debates.models import Debate, DebateResult
from chat.models import Message
from exams.models import Quiz

@receiver(post_save, sender=Notice)
def notify_notice(sender, instance, created, **kwargs):
    if created:
        if instance.target_role == 'all':
            users = User.objects.exclude(pk=instance.posted_by.pk)
        else:
            users = User.objects.filter(role=instance.target_role).exclude(pk=instance.posted_by.pk)
        
        for user in users:
            Notification.objects.create(
                user=user,
                title="📢 New Notice",
                message=f"{instance.posted_by.get_full_name()} posted: {instance.title}",
                notification_type=Notification.Type.NOTICE,
                link=reverse('portal:notice_list')
            )

@receiver(post_save, sender=Assignment)
def notify_assignment(sender, instance, created, **kwargs):
    if created:
        students = User.objects.filter(role=User.Role.STUDENT)
        for student in students:
            Notification.objects.create(
                user=student,
                title="📝 New Assignment",
                message=f"New assignment: {instance.title}",
                notification_type=Notification.Type.ASSIGNMENT,
                link=reverse('portal:assignment_list')
            )

@receiver(post_save, sender=Debate)
def notify_debate(sender, instance, created, **kwargs):
    if created:
        users = User.objects.exclude(pk=instance.created_by.pk)
        for user in users:
            Notification.objects.create(
                user=user,
                title="⚖️ New Debate Scheduled",
                message=f"A new debate '{instance.title}' has been scheduled for {instance.date}.",
                notification_type=Notification.Type.DEBATE,
                link=reverse('debates:detail', kwargs={'pk': instance.pk})
            )

@receiver(post_save, sender=Message)
def notify_message(sender, instance, created, **kwargs):
    if created:
        participants = instance.room.participants.exclude(pk=instance.sender.pk)
        for user in participants:
            Notification.objects.create(
                user=user,
                title=f"💬 Message from {instance.sender.get_full_name()}",
                message=instance.content[:100],
                notification_type=Notification.Type.CHAT,
                link=reverse('chat:room_detail', kwargs={'pk': instance.room.pk})
            )

@receiver(post_save, sender=Quiz)
def notify_quiz(sender, instance, created, **kwargs):
    if created:
        students = User.objects.filter(role=User.Role.STUDENT)
        for student in students:
            Notification.objects.create(
                user=student,
                title="🎓 New Exam/Quiz",
                message=f"A new quiz '{instance.title}' is now available.",
                notification_type=Notification.Type.NOTICE,
                link=reverse('exams:quiz_list')
            )

@receiver(post_save, sender=DebateResult)
def notify_debate_result(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.student,
            title="🏆 Debate Result Out",
            message=f"Your result for '{instance.debate.title}' has been published.",
            notification_type=Notification.Type.RESULT,
            link=reverse('debates:detail', kwargs={'pk': instance.debate.pk})
        )

@receiver(m2m_changed, sender=SharedFile.shared_with.through)
def notify_file_shared(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            try:
                user = User.objects.get(pk=user_id)
                Notification.objects.create(
                    user=user,
                    title="📁 File Shared with You",
                    message=f"{instance.uploaded_by.get_full_name()} shared: {instance.title}",
                    notification_type=Notification.Type.SYSTEM,
                    link=reverse('portal:file_list')
                )
            except User.DoesNotExist:
                pass
