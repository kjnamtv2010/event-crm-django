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