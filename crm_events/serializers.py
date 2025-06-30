from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Event, CustomUser
from .token_utils import decrypt_event_token

User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the CustomUser model, including aggregated event counts.
    """
    total_owned_events = serializers.IntegerField(read_only=True)
    total_hosting_events = serializers.IntegerField(read_only=True)
    total_attended_events = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'company', 'job_title', 'city', 'state',
            'date_joined',
            'total_owned_events', 'total_hosting_events', 'total_attended_events'
        )

    def create(self, validated_data):
        """
        Creates a new CustomUser instance, handling password hashing.
        """
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password is not None:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        """
        Updates an existing CustomUser instance, handling password hashing.
        """
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


class EmailSendSerializer(serializers.Serializer):
    """
    Serializer for sending emails to users based on various filters.
    """
    company = serializers.CharField(required=False, max_length=100)
    job_title = serializers.CharField(required=False, max_length=100)
    city = serializers.CharField(required=False, max_length=100)
    state = serializers.CharField(required=False, max_length=100)
    total_hosting_events_min = serializers.IntegerField(required=False, min_value=0)
    total_hosting_events_max = serializers.IntegerField(required=False, min_value=0)

    total_attended_events_min = serializers.IntegerField(required=False, min_value=0)
    total_attended_events_max = serializers.IntegerField(required=False, min_value=0)

    subject = serializers.CharField(max_length=255, help_text="Subject of the email.")
    body = serializers.CharField(help_text="Body content of the email (plain text).")

    event_slug = serializers.CharField(
        required=False, max_length=200, help_text="Slug of the event to link this email to."
    )

    def validate(self, data):
        """
        Validates email content, event slug existence, and min/max ranges for event counts.
        """
        if not data.get('body'):
            raise serializers.ValidationError(
                {"body": "Email body plain text must be provided."})

        event_slug = data.get('event_slug')
        if event_slug and not Event.objects.filter(slug=event_slug).exists():
            raise serializers.ValidationError(
                {"event_slug": "Event with this slug does not exist."})

        if 'total_hosting_events_min' in data and 'total_hosting_events_max' in data and \
                data['total_hosting_events_min'] > data['total_hosting_events_max']:
            raise serializers.ValidationError(
                {"total_hosting_events_max": "Min cannot be greater than max for hosting events."})

        if 'total_attended_events_min' in data and 'total_attended_events_max' in data and \
                data['total_attended_events_min'] > data['total_attended_events_max']:
            raise serializers.ValidationError({
                                                "total_attended_events_max": "Min cannot be greater than max for attended events."})

        return data


class EventSerializer(serializers.ModelSerializer):
    """
    Basic serializer for the Event model, exposing slug and title.
    """
    class Meta:
        model = Event
        fields = ('slug', 'title')


class EventDetailAndRegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed event information, including related user data (owner, hosts, attendees).
    Now using a single 'participants' M2M relationship with a 'through' model.
    """
    owner = CustomUserSerializer(read_only=True)
    hosts = serializers.SerializerMethodField()
    attendees = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'slug', 'title', 'description', 'start_at', 'end_at', 'venue',
            'max_capacity', 'owner', 'hosts', 'attendees'
        ]
        lookup_field = 'slug'

    def get_hosts(self, obj):
        hosts_queryset = obj.get_hosts()
        return CustomUserSerializer(hosts_queryset, many=True).data

    def get_attendees(self, obj):
        attendees_queryset = obj.get_attendees()
        return CustomUserSerializer(attendees_queryset, many=True).data


class EventManageUserActionSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, help_text="Encrypted token for identifying user and expiry.")

    is_host = serializers.BooleanField(default=False, help_text="Set user as Host.")
    is_attend = serializers.BooleanField(default=False, help_text="Set user as Attendee.")

    utm_source = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    utm_medium = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    utm_campaign = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    utm_term = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    utm_content = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    session_id = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)

    user_to_manage = None

    def validate(self, data):
        token = data.get("token")
        email, user_id, expiry_dt = decrypt_event_token(token)

        if not email or not user_id:
            raise serializers.ValidationError("Invalid or expired token/ expired event")

        try:
            self.user_to_manage = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found for given token.")

        if data.get('is_host') and data.get('is_attend'):
            raise serializers.ValidationError(
                "A user cannot be both a Host and an Attendee simultaneously."
            )

        return data



class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email']

class SimpleEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['title']