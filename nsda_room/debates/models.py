from django.db import models
from django.conf import settings
from django.urls import reverse


class Debate(models.Model):
    """A debate event."""

    class Format(models.TextChoices):
        LINCOLN_DOUGLAS = 'ld', 'Lincoln-Douglas'
        PUBLIC_FORUM = 'pf', 'Public Forum'
        POLICY = 'policy', 'Policy'
        CONGRESS = 'congress', 'Congressional Debate'
        EXTEMP = 'extemp', 'Extemporaneous'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', 'Upcoming'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=255)
    description = models.TextField()
    format = models.CharField(
        max_length=20,
        choices=Format.choices,
        default=Format.LINCOLN_DOUGLAS,
    )
    topic = models.TextField(blank=True, help_text='Resolution or topic for this debate')
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPCOMING,
    )
    max_participants = models.PositiveIntegerField(default=20)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_debates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.title} ({self.get_format_display()})"

    def get_absolute_url(self):
        return reverse('debates:detail', kwargs={'pk': self.pk})

    @property
    def registered_count(self):
        return self.registrations.count()

    @property
    def is_full(self):
        return self.registered_count >= self.max_participants

    @property
    def spots_left(self):
        return max(0, self.max_participants - self.registered_count)


class DebateRegistration(models.Model):
    """Student registration for a debate."""

    class Team(models.TextChoices):
        AFFIRMATIVE = 'aff', 'Affirmative'
        NEGATIVE = 'neg', 'Negative'
        UNASSIGNED = 'na', 'Unassigned'

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='registrations',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debate_registrations',
    )
    team = models.CharField(
        max_length=5,
        choices=Team.choices,
        default=Team.UNASSIGNED,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['debate', 'student']
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.student.username} → {self.debate.title}"


class DebateRound(models.Model):
    """A round within a debate."""

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='rounds',
    )
    round_number = models.PositiveIntegerField()
    topic = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['debate', 'round_number']
        ordering = ['round_number']

    def __str__(self):
        return f"Round {self.round_number} - {self.debate.title}"


class DebateResult(models.Model):
    """Results and feedback for a student in a debate."""

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='results',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debate_results',
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    rank = models.PositiveIntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='graded_results',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['debate', 'student']
        ordering = ['rank', '-score']

    def __str__(self):
        return f"{self.student.username} - {self.debate.title}: {self.score}"
