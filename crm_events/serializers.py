from rest_framework import serializers
from crm_events.models import CustomUser


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomUser model.
    Includes counts of owned, hosting, and registered events as read-only fields.
    """
    total_owned_events = serializers.IntegerField(read_only=True)
    total_hosting_events = serializers.IntegerField(read_only=True)
    total_registered_events = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'gender', 'job_title', 'company', 'city', 'state',
            'total_owned_events', 'total_hosting_events', 'total_registered_events',
        ]

    def get_total_owned_events(self, obj):
        if hasattr(obj, 'total_owned_events'):
            return obj.total_owned_events
        return obj.owned_events.count()

    def get_total_hosting_events(self, obj):
        if hasattr(obj, 'total_hosting_events'):
            return obj.total_hosting_events
        return obj.hosting_events.count()

    def get_total_registered_events(self, obj):
        if hasattr(obj, 'total_registered_events'):
            return obj.total_registered_events
        return obj.event_registrations.count()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser.objects.create(**validated_data)
        if password is not None:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


class EmailSendSerializer(serializers.Serializer):
    """
    Serializer for the email sending endpoint.
    Includes filter criteria for users and email content.
    """
    company = serializers.CharField(required=False, max_length=100)
    job_title = serializers.CharField(required=False, max_length=100)
    city = serializers.CharField(required=False, max_length=100)
    state = serializers.CharField(required=False, max_length=100)
    total_hosting_events_min = serializers.IntegerField(required=False, min_value=0)
    total_hosting_events_max = serializers.IntegerField(required=False, min_value=0)
    total_registered_events_min = serializers.IntegerField(required=False, min_value=0)
    total_registered_events_max = serializers.IntegerField(required=False, min_value=0)

    # Email content
    subject = serializers.CharField(max_length=255, help_text="Subject of the email.")
    body = serializers.CharField(help_text="Body content of the email.")

    def validate(self, data):
        if not data.get('body') and not data.get('html_body'):
            raise serializers.ValidationError("Either 'body' or 'html_body' must be provided.")
        return data
