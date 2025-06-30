from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser to add
    additional profile fields.
    """
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    gender_choices = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=1, choices=gender_choices, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    company = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    state = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="customuser_set",
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_set",
        related_query_name="customuser",
    )

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username or self.email or f"User {self.id}"


class Event(models.Model):
    """
    Model representing an event.
    """
    slug = models.SlugField(unique=True, max_length=200)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    venue = models.CharField(max_length=255, blank=True, null=True)
    max_capacity = models.IntegerField(blank=True, null=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_events',
        help_text="The user who created and manages this event."
    )

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='EventParticipation',
        related_name='participated_events',
        blank=True,
        help_text="Users participating in the event as either hosts or attendees."
    )

    class Meta:
        db_table = 'events'

    def __str__(self):
        return f"{self.slug} - Title: {self.title}"

    def get_hosts(self):
        return CustomUser.objects.filter(
            eventparticipations__event=self,
            eventparticipations__role='host'
        )

    def get_attendees(self):
        return CustomUser.objects.filter(
            eventparticipations__event=self,
            eventparticipations__role='attendee'
        )


class EventParticipation(models.Model):
    ROLE_HOST = 'host'
    ROLE_ATTENDEE = 'attendee'
    """
    Intermediate model to manage user participation in events,
    including their role (host/attendee).
    """
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='eventparticipations'
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='eventparticipations'
    )

    ROLE_CHOICES = [
        ('host', 'Host'),
        ('attendee', 'Attendee'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        db_table = 'event_participation'

    def __str__(self):
        return f"{self.user.username} as {self.role} in {self.event.title}"


class EmailLog(models.Model):
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True, null=True)
    filters_applied = models.JSONField(blank=True, null=True)
    recipients = models.JSONField()

    sent_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='sent_emails')
    sent_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PARTIAL_SUCCESS', 'Partial Success')
    ])
    error_message = models.TextField(blank=True, null=True)
    num_recipients = models.IntegerField(default=0)
    num_sent_successfully = models.IntegerField(default=0)
    event = models.ForeignKey(
        'Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs'
    )

    class Meta:
        ordering = ['-sent_at']
        db_table = 'email_log'


class UTMData(models.Model):
    utm_source = models.CharField(max_length=255, blank=True, null=True)
    utm_medium = models.CharField(max_length=255, blank=True, null=True)
    utm_campaign = models.CharField(max_length=255, blank=True, null=True)
    utm_term = models.CharField(max_length=255, blank=True, null=True)
    utm_content = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='utm_data_records')
    session_id = models.CharField(max_length=255, blank=True, null=True)

    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='utm_data_entries')

    ROLE_CHOICES = [
        ('host', 'Host'),
        ('attendee', 'Attendee'),
        ('unregistered', 'Unregistered')  # For when roles are removed
    ]
    role_change_type = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)

    class Meta:
        db_table = 'utm_data'
