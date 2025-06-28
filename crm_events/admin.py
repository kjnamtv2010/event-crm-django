from django.contrib import admin
from crm_events.models import Event, CustomUser
from django.contrib.auth.admin import UserAdmin


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_at', 'end_at', 'owner', 'max_capacity')
    list_filter = ('start_at', 'end_at', 'owner', 'hosts')
    search_fields = ('title', 'description', 'venue')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'start_at'
    filter_horizontal = ('hosts',)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'company', 'job_title', 'city', 'state', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined', 'company', 'city', 'state')
    search_fields = ('username', 'email', 'company', 'job_title', 'city', 'state')
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone_number', 'avatar', 'gender', 'job_title', 'company', 'city', 'state')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone_number', 'avatar', 'gender', 'job_title', 'company', 'city', 'state')}),
    )
