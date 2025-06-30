from django.contrib import admin
from .models import Event, CustomUser, EventParticipation
from django.contrib.auth.admin import UserAdmin


class EventParticipationInline(admin.TabularInline):
    """
    Inline admin for EventParticipation to manage hosts and attendees directly within the Event admin page.
    """
    model = EventParticipation
    extra = 1


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'start_at', 'end_at', 'owner', 'max_capacity', 'display_hosts_count',
                    'display_attendees_count')
    list_filter = ('start_at', 'end_at', 'owner')
    search_fields = ('title', 'description', 'venue', 'owner__username', 'owner__email')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'start_at'

    inlines = [EventParticipationInline]

    def display_hosts_count(self, obj):
        return obj.get_hosts().count()

    display_hosts_count.short_description = 'Hosts Count'
    display_hosts_count.admin_order_field = 'eventparticipation__role'

    def display_attendees_count(self, obj):
        return obj.get_attendees().count()

    display_attendees_count.short_description = 'Attendees Count'
    display_attendees_count.admin_order_field = 'eventparticipation__role'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'company', 'job_title', 'city', 'state', 'is_staff',
                    'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined', 'company', 'city', 'state')
    search_fields = ('username', 'email', 'company', 'job_title', 'city', 'state')
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        (None,
         {'fields': ('phone_number', 'avatar', 'gender', 'job_title', 'company', 'city', 'state')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None,
         {'fields': ('phone_number', 'avatar', 'gender', 'job_title', 'company', 'city', 'state')}),
    )


@admin.register(EventParticipation)
class EventParticipationAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_email', 'event', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'user__email', 'event__title')
    readonly_fields = ('user', 'event', 'role', 'joined_at')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
