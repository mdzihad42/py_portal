from django.db.models.signals import post_save
from django.dispatch import receiver

from debates.models import DebateRegistration, DebateResult
from portal.models import Notice, AssignmentSubmission
from .models import Notification


@receiver(post_save, sender=DebateRegistration)
def notify_debate_registration(sender, instance, created, **kwargs):
    """Notify when a student registers for a debate."""
    if created:
        # Notify the teacher who created the debate
        Notification.objects.create(
            user=instance.debate.created_by,
            title='New Debate Registration',
            message=f'{instance.student.get_full_name() or instance.student.username} registered for "{instance.debate.title}".',
            notification_type=Notification.Type.DEBATE,
            link=f'/debates/{instance.debate.pk}/',
        )


@receiver(post_save, sender=DebateResult)
def notify_debate_result(sender, instance, created, **kwargs):
    """Notify student when a result is posted."""
    if created:
        Notification.objects.create(
            user=instance.student,
            title='New Debate Result',
            message=f'Your result for "{instance.debate.title}" has been posted. Score: {instance.score}',
            notification_type=Notification.Type.RESULT,
            link=f'/debates/{instance.debate.pk}/',
        )


@receiver(post_save, sender=Notice)
def notify_notice_posted(sender, instance, created, **kwargs):
    """Notify users when a new notice is posted."""
    if created:
        from accounts.models import User
        if instance.target_role == 'all':
            users = User.objects.exclude(pk=instance.posted_by.pk)
        elif instance.target_role == 'student':
            users = User.objects.filter(role='student')
        else:
            users = User.objects.filter(role='teacher').exclude(pk=instance.posted_by.pk)

        notifications = [
            Notification(
                user=user,
                title='New Notice',
                message=f'"{instance.title}" posted by {instance.posted_by.get_full_name() or instance.posted_by.username}.',
                notification_type=Notification.Type.NOTICE,
                link=f'/notices/{instance.pk}/',
            )
            for user in users
        ]
        Notification.objects.bulk_create(notifications)


@receiver(post_save, sender=AssignmentSubmission)
def notify_assignment_submission(sender, instance, created, **kwargs):
    """Notify teacher when a student submits an assignment."""
    if created:
        Notification.objects.create(
            user=instance.assignment.created_by,
            title='Assignment Submitted',
            message=f'{instance.student.get_full_name() or instance.student.username} submitted "{instance.assignment.title}".',
            notification_type=Notification.Type.ASSIGNMENT,
            link=f'/assignments/{instance.assignment.pk}/',
        )
    elif instance.is_graded:
        Notification.objects.create(
            user=instance.student,
            title='Assignment Graded',
            message=f'Your submission for "{instance.assignment.title}" has been graded. Score: {instance.grade}',
            notification_type=Notification.Type.ASSIGNMENT,
            link=f'/assignments/{instance.assignment.pk}/',
        )
