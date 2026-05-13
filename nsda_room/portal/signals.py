from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import Notice, SharedFile, Assignment
from notifications.models import Notification
from accounts.models import User

@receiver(post_save, sender=Notice)
def notify_new_notice(sender, instance, created, **kwargs):
    if created:
        # Determine target users
        if instance.target_role == 'all':
            users = User.objects.exclude(pk=instance.posted_by.pk)
        else:
            users = User.objects.filter(role=instance.target_role).exclude(pk=instance.posted_by.pk)
        
        for user in users:
            Notification.objects.create(
                user=user,
                title="New Notice Posted",
                message=f"A new notice has been posted: {instance.title}",
                notification_type=Notification.Type.NOTICE,
                link="/portal/notices/"
            )

@receiver(post_save, sender=Assignment)
def notify_new_assignment(sender, instance, created, **kwargs):
    if created:
        # Assignments are usually for students
        students = User.objects.filter(role='student')
        for student in students:
            Notification.objects.create(
                user=student,
                title="New Assignment",
                message=f"Teacher {instance.created_by.get_full_name()} created a new assignment: {instance.title}",
                notification_type=Notification.Type.ASSIGNMENT,
                link="/portal/assignments/"
            )

@receiver(m2m_changed, sender=SharedFile.shared_with.through)
def notify_file_shared(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for user_id in pk_set:
            user = User.objects.get(pk=user_id)
            Notification.objects.create(
                user=user,
                title="File Shared with You",
                message=f"{instance.uploaded_by.get_full_name()} shared a file: {instance.title}",
                notification_type=Notification.Type.SYSTEM,
                link="/portal/files/"
            )
