from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


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
    job_title = models.CharField(max_length=100, blank=True, null=True)
    company = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="customuser_set",  # Unique related_name for custom user
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_set",  # Unique related_name for custom user
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
        related_name='owned_events'
    )

    hosts = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='hosting_events',
        blank=True
    )

    class Meta:
        db_table = 'events'

    def __str__(self):
        return self.title


class EventRegistration(models.Model):
    """
    Model representing a user's registration for an event.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_registrations'
    )
    # ForeignKey to Event
    event = models.ForeignKey(
        'Event',
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    registered_at = models.DateTimeField(
        auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        db_table = 'event_registrations'
