import json
import logging
from urllib.parse import urlencode
from typing import Any, Dict, Optional
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.urls import reverse
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
from .services import (
    apply_user_filters, get_filter_applies,
    filter_email_logs, filter_and_sort_utm_records,
    manage_event_user_role,
    record_utm_data_for_event_role_change
)

logger = logging.getLogger(__name__)


# --- UI Views ---
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

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Adds additional context data for event ownership and hosting status.
        """
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        user = self.request.user

        context['is_owner'] = False
        context['viewer_is_hosting'] = False

        if user.is_authenticated:
            context['is_owner'] = user == event.owner
            context['viewer_is_hosting'] = event.hosts.filter(pk=user.pk).exists()
        return context


# --- API Views ---
class CustomUserFilterView(APIView):
    """
    API endpoint for filtering and paginating CustomUser instances.

    Supports filtering by various user attributes and event counts (owned, hosted, attended).
    """

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Handles GET requests to retrieve filtered and paginated user data.
        """
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
        """
        Handles GET requests to retrieve all events, ordered by start time.
        """
        events = Event.objects.all().order_by('start_at')
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SendEmailsView(APIView):
    """
    API endpoint for sending emails to filtered users.

    Supports linking emails to an event and including UTM parameters.
    """

    def post(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Handles POST requests to send emails based on user filters.
        """
        serializer = EmailSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        subject = validated_data['subject']
        plain_body_content = validated_data['body']
        event_slug = validated_data.get('event_slug')
        sender_user = CustomUser.objects.filter(
            is_superuser=True, is_active=True, username='admin'
        ).last()

        queryset = CustomUser.objects.all()
        queryset = apply_user_filters(queryset, validated_data)
        recipient_list = [user.email for user in queryset if user.email]

        if not recipient_list:
            logger.info("No users found matching the filter criteria for email sending. No emails sent.")
            return Response(
                {"message": "No users found matching the filter criteria. No emails sent."},
                status=status.HTTP_200_OK
            )

        event_obj: Optional[Event] = None
        if event_slug:
            try:
                event_obj = Event.objects.get(slug=event_slug)
                current_host = request.get_host()
                scheme = 'https' if request.is_secure() else 'http'
                base_domain_with_scheme = f"{scheme}://{current_host}"
                event_page_path = reverse('event-detail-page', kwargs={'slug': event_slug})
                base_url = base_domain_with_scheme.rstrip('/') + event_page_path

                utm_params = {
                    'utm_source': "crm_email",
                    'utm_medium': "email",
                    'utm_campaign': f"event_{event_slug.replace('-', '_')}",
                    'utm_content': "text_link"
                }
                event_link = f"{base_url}?{urlencode(utm_params)}"

                plain_body_content = plain_body_content.replace('{event_link}', event_link) \
                                                       if '{event_link}' in plain_body_content else \
                                                       f"{plain_body_content}\n\nFind more details here: {event_link}"

            except Event.DoesNotExist:
                logger.error(f"Event with slug '{event_slug}' not found for email, despite serializer validation.")
                return Response({"message": "Internal server error: Linked event not found."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                logger.exception(f"Error building event link for slug '{event_slug}': {e}")
                return Response({"message": f"Error processing event link: {e}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        email_log = EmailLog(
            subject=subject,
            body=plain_body_content,
            filters_applied=get_filter_applies(validated_data),
            recipients=json.dumps(recipient_list),
            sent_by=sender_user,
            num_recipients=len(recipient_list),
            status='PENDING',
            event=event_obj
        )
        email_log.save()

        try:
            email_kwargs = {
                'subject': subject,
                'message': plain_body_content,
                'from_email': settings.DEFAULT_FROM_EMAIL,
                'recipient_list': recipient_list,
                'fail_silently': False,
            }

            num_sent = send_mail(**email_kwargs)

            email_log.num_sent_successfully = num_sent
            if num_sent == len(recipient_list):
                email_log.status = 'SUCCESS'
            elif num_sent > 0:
                email_log.status = 'PARTIAL_SUCCESS'
            else:
                email_log.status = 'FAILED'
            email_log.save()
            logger.info(f"Successfully initiated sending emails to {len(recipient_list)} recipients. {num_sent} sent. Log ID: {email_log.id}")
            return Response({
                "message": f"Emails sent successfully to {num_sent} recipients.",
                "recipients_count": len(recipient_list),
                "sent_count": num_sent
            }, status=status.HTTP_200_OK)
        except Exception as e:
            email_log.status = 'FAILED'
            email_log.error_message = str(e)
            email_log.save()
            logger.exception(f"Failed to send emails. Error: {e}")
            return Response({"error": f"Failed to send emails: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventDetailAndRegisterView(APIView):
    """
    API endpoint for retrieving event details and managing user registration/hosting for an event.
    """

    def get(self, request: Any, slug: str, *args: Any, **kwargs: Any) -> Response:
        """
        Handles GET requests to retrieve details for a specific event.
        """
        event = get_object_or_404(Event, slug=slug)
        serializer = EventDetailAndRegisterSerializer(event)
        return Response(serializer.data)

    def post(self, request: Any, slug: str, *args: Any, **kwargs: Any) -> Response:
        """
        Handles POST requests to manage a user's role (host/attendee) for an event.

        Includes logic for recording UTM data and handling capacity limits.
        """
        event = get_object_or_404(Event, slug=slug)

        serializer = EventManageUserActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_to_manage = serializer.user_to_manage
        desired_is_host = serializer.validated_data.get('is_host', False)
        desired_is_attend = serializer.validated_data.get('is_attend', False)

        # Trích xuất dữ liệu UTM từ request
        utm_data_fields_from_request = {
            'utm_source': serializer.validated_data.get('utm_source'),
            'utm_medium': serializer.validated_data.get('utm_medium'),
            'utm_campaign': serializer.validated_data.get('utm_campaign'),
            'utm_term': serializer.validated_data.get('utm_term'),
            'utm_content': serializer.validated_data.get('utm_content'),
            'session_id': serializer.validated_data.get('session_id'),
        }
        utm_data_fields_to_save = {k: v for k, v in utm_data_fields_from_request.items() if
                                    v is not None and v != ''}
        has_utm_params = bool(utm_data_fields_to_save)

        # Gọi service để quản lý vai trò người dùng trong sự kiện
        role_management_result = manage_event_user_role(
            event=event,
            user=user_to_manage,
            desired_is_host=desired_is_host,
            desired_is_attend=desired_is_attend
        )

        messages = role_management_result['messages']
        status_code = role_management_result['status_code']
        actual_role_change_performed = role_management_result['actual_role_change_performed']
        final_role_change_type = role_management_result['final_role_change_type']
        user_status_updated = role_management_result['current_status']

        # Nếu có thay đổi vai trò và có tham số UTM, ghi lại dữ liệu UTM
        if actual_role_change_performed and final_role_change_type and has_utm_params:
            utm_record_result = record_utm_data_for_event_role_change(
                user=user_to_manage,
                event=event,
                role_change_type=final_role_change_type,
                utm_data_fields=utm_data_fields_to_save
            )
            messages.append(utm_record_result['message'])
        elif actual_role_change_performed and not has_utm_params:
            messages.append("Role changed, but no UTM data provided to record.")

        # Refresh lại event object để đảm bảo lấy được trạng thái mới nhất (ví dụ: số lượng attendees/hosts)
        # sau khi service đã thay đổi và lưu vào DB.
        event.refresh_from_db()
        updated_event_data = EventDetailAndRegisterSerializer(event).data

        return Response({
            "message": " ".join(messages),
            "user_status_updated": user_status_updated,
            "event_data": updated_event_data
        }, status=status_code)


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
