import json
import logging
from typing import Any, Dict
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, TemplateView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomUser, EmailLog, Event, UTMData
from .serializers import (
    CustomUserSerializer,
    EmailSendSerializer,
    EventDetailAndRegisterSerializer,
    EventManageUserActionSerializer,
    EventSerializer,
)
from crm_events.services.services import (
    apply_user_filters, get_filter_applies,
    filter_email_logs, filter_and_sort_utm_records,
    handle_event_user_registration
)
from crm_events.services.email_services import send_bulk_event_emails

logger = logging.getLogger(__name__)


class UserFilterPageView(TemplateView):
    """
    Renders the user filter page.
    """
    template_name = 'crm_events/user_filter_page.html'


class EventDetailPageView(DetailView):
    """
    Displays the details of a single event.
    """
    model = Event
    template_name = 'crm_events/event_detail_page.html'
    context_object_name = 'event'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        user = self.request.user

        context['is_owner'] = False
        context['viewer_is_hosting'] = False

        context['hosts'] = event.get_hosts()
        context['attendees'] = event.get_attendees()

        if user.is_authenticated:
            context['is_owner'] = user == event.owner
            context['viewer_is_hosting'] = event.get_hosts().filter(pk=user.pk).exists()
        return context


class CustomUserFilterView(APIView):
    """
    API endpoint for filtering and paginating CustomUser instances.

    Supports filtering by various user attributes and event counts (owned, hosted, attended).
    """

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        queryset = CustomUser.objects.all()
        query_params = request.query_params

        integer_params = [
            'total_owned_events_min', 'total_owned_events_max',
            'total_hosting_events_min', 'total_hosting_events_max',
            'total_attended_events_min', 'total_attended_events_max'
        ]
        for param in integer_params:
            if query_params.get(param):
                try:
                    int(query_params[param])
                except ValueError:
                    return Response({"error": f"{param} must be an integer."},
                                    status=status.HTTP_400_BAD_REQUEST)

        queryset = apply_user_filters(queryset, query_params)

        order_by = query_params.get('ordering')
        valid_ordering_fields = [
            'username', '-username', 'email', '-email', 'date_joined', '-date_joined',
            'total_owned_events', '-total_owned_events',
            'total_hosting_events', '-total_hosting_events',
            'total_attended_events', '-total_attended_events',
            'company', '-company', 'city', '-city', 'state', '-state', 'job_title', '-job_title'
        ]
        if order_by and order_by in valid_ordering_fields:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('username')

        paginator = PageNumberPagination()
        page_size = request.query_params.get('page_size', 10)
        try:
            paginator.page_size = int(page_size)
        except ValueError:
            return Response({"error": "page_size must be an integer"},
                            status=status.HTTP_400_BAD_REQUEST)

        page = paginator.paginate_queryset(queryset, request, view=self)

        if page is not None:
            serializer = CustomUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CustomUserSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventListView(APIView):
    """
    API endpoint for retrieving a list of events.
    """

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        events = Event.objects.all().order_by('start_at')
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SendEmailsView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = EmailSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        subject = validated_data['subject']
        body = validated_data['body']
        event_slug = validated_data.get('event_slug')

        sender_user = CustomUser.objects.filter(is_superuser=True, is_active=True, username='admin').last()
        queryset = apply_user_filters(CustomUser.objects.all(), validated_data)
        users = [user for user in queryset if user.email]

        if not users:
            return Response({"message": "No users found matching filter criteria."}, status=status.HTTP_200_OK)

        try:
            num_success, total = send_bulk_event_emails(
                subject=subject,
                body_template=body,
                users=users,
                event_slug=event_slug,
                sender_user=sender_user,
                filters_applied=get_filter_applies(validated_data),
                request=request
            )
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": f"Emails sent. {num_success} out of {total} succeeded.",
            "sent_count": num_success,
            "recipients_count": total
        }, status=status.HTTP_200_OK)


class EventDetailAndRegisterView(APIView):
    def get(self, request, slug, *args, **kwargs):
        event = get_object_or_404(Event, slug=slug)
        serializer = EventDetailAndRegisterSerializer(event)
        return Response(serializer.data)

    def post(self, request, slug, *args, **kwargs):
        event = get_object_or_404(Event, slug=slug)

        serializer = EventManageUserActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.user_to_manage
        is_host = serializer.validated_data.get('is_host', False)
        is_attend = serializer.validated_data.get('is_attend', False)

        utm_data_fields = {
            k: v for k, v in serializer.validated_data.items()
            if (k.startswith('utm_') or k == 'session_id') and v
        }

        result = handle_event_user_registration(
            event=event,
            user=user,
            is_host=is_host,
            is_attend=is_attend,
            utm_data_fields=utm_data_fields
        )

        return Response({
            "message": " ".join(result["messages"]),
            "user_status_updated": result["user_status_updated"],
            "event_data": result["updated_event_data"]
        }, status=result["status_code"])


class UTMAnalysisView(TemplateView):
    """
    Displays a paginated list of UTM data records with search and filter options.
    """
    template_name = 'crm_events/utm_data_list.html'
    paginate_by = 20

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Retrieves and filters UTM data for display, including pagination and analytics.
        """
        context = super().get_context_data(**kwargs)

        utm_records = UTMData.objects.select_related('user', 'event')
        utm_records, sort_by = filter_and_sort_utm_records(utm_records, self.request.GET)

        paginator = Paginator(utm_records, self.paginate_by)
        page = self.request.GET.get('page')
        try:
            paged_utm_records = paginator.page(page)
        except PageNotAnInteger:
            paged_utm_records = paginator.page(1)
        except EmptyPage:
            paged_utm_records = paginator.page(paginator.num_pages)

        context['utm_records'] = paged_utm_records
        context['page_obj'] = paged_utm_records

        current_query_params = self.request.GET.copy()
        if 'page' in current_query_params:
            del current_query_params['page']

        context['current_query_params'] = current_query_params.urlencode()
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['filter_source'] = self.request.GET.get('source', '').strip()
        context['filter_medium'] = self.request.GET.get('medium', '').strip()
        context['filter_campaign'] = self.request.GET.get('campaign', '').strip()
        context['filter_role'] = self.request.GET.get('role', '').strip()
        context['sort_by'] = sort_by

        context['total_records'] = utm_records.count()
        context['unique_users'] = utm_records.values('user').distinct().count()
        context['unique_events'] = utm_records.values('event').distinct().count()

        return context


class EmailTrackerTemplateView(TemplateView):
    template_name = 'crm_events/email_status_tracker.html'

def email_log_json_view(request):
    """
    API endpoint for retrieving a paginated list of email logs with filter and sort options.
    """
    queryset = EmailLog.objects.select_related('sent_by', 'event').all()
    queryset = filter_email_logs(queryset, request.GET)

    page = request.GET.get('page', 1)
    page_size = 10
    paginator = Paginator(queryset, page_size)

    try:
        email_logs_page = paginator.page(page)
    except PageNotAnInteger:
        email_logs_page = paginator.page(1)
    except EmptyPage:
        email_logs_page = paginator.page(paginator.num_pages)

    results = []
    for log in email_logs_page:
        results.append({
            'id': log.id,
            'subject': log.subject,
            'body_snippet': log.body[:100] + '...' if len(log.body) > 100 else log.body,
            'recipients': json.loads(log.recipients) if log.recipients else [],
            'sent_by': {
                'username': log.sent_by.username,
                'email': log.sent_by.email
            } if log.sent_by else None,
            'sent_at': log.sent_at.isoformat() if log.sent_at else None,
            'status': log.status,
            'error_message': log.error_message,
            'num_recipients': log.num_recipients,
            'num_sent_successfully': log.num_sent_successfully,
            'event': {
                'title': log.event.title,
                'slug': log.event.slug
            } if log.event else None,
            'filters_applied': log.filters_applied
        })

    response_data = {
        'results': results,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page_number': email_logs_page.number,
        'page_size': page_size,
        'has_next': email_logs_page.has_next(),
        'has_previous': email_logs_page.has_previous(),
    }
    return JsonResponse(response_data)
