import logging
from django.db import transaction
from django.db.models import Count, Q
from .models import CustomUser, Event, UTMData

logger = logging.getLogger(__name__)


def get_filter_applies(validated_data):
    """
    Extracts and cleans user filter parameters from validated data,
    excluding email content fields.
    """
    filters_applied = {}
    email_content_fields = ['subject', 'body', 'event_slug']

    for field, value in validated_data.items():
        if field in email_content_fields:
            continue

        if value is not None:
            if isinstance(value, str):
                trimmed_value = value.strip()
                if trimmed_value:
                    filters_applied[field] = trimmed_value
            else:
                filters_applied[field] = value
    return filters_applied


def apply_user_filters(queryset, filters):
    """
    Applies filters to a CustomUser queryset based on provided filter parameters.
    Includes filtering by company, job title, city, state, and event counts.
    """
    queryset = queryset.annotate(
        total_owned_events=Count('owned_events', distinct=True),
        total_hosting_events=Count('hosted_events', distinct=True),
        total_attended_events=Count('attended_events', distinct=True)
    )

    if filters.get('company'):
        queryset = queryset.filter(company__icontains=filters['company'])
    if filters.get('job_title'):
        queryset = queryset.filter(job_title__icontains=filters['job_title'])
    if filters.get('city'):
        queryset = queryset.filter(city__icontains=filters['city'])
    if filters.get('state'):
        queryset = queryset.filter(state__icontains=filters['state'])

    total_owned_events_min = filters.get('total_owned_events_min')
    if total_owned_events_min is not None:
        try:
            queryset = queryset.filter(total_owned_events__gte=int(total_owned_events_min))
        except ValueError:
            pass

    total_owned_events_max = filters.get('total_owned_events_max')
    if total_owned_events_max is not None:
        try:
            queryset = queryset.filter(total_owned_events__lte=int(total_owned_events_max))
        except ValueError:
            pass

    total_hosting_events_min = filters.get('total_hosting_events_min')
    if total_hosting_events_min is not None:
        try:
            queryset = queryset.filter(total_hosting_events__gte=int(total_hosting_events_min))
        except ValueError:
            pass

    total_hosting_events_max = filters.get('total_hosting_events_max')
    if total_hosting_events_max is not None:
        try:
            queryset = queryset.filter(total_hosting_events__lte=int(total_hosting_events_max))
        except ValueError:
            pass

    total_attended_events_min = filters.get('total_attended_events_min')
    if total_attended_events_min is not None:
        try:
            queryset = queryset.filter(total_attended_events__gte=int(total_attended_events_min))
        except ValueError:
            pass

    total_attended_events_max = filters.get('total_attended_events_max')
    if total_attended_events_max is not None:
        try:
            queryset = queryset.filter(total_attended_events__lte=int(total_attended_events_max))
        except ValueError:
            pass

    return queryset


def filter_email_logs(queryset, request_get_params):
    """
    Applies filters and ordering to an EmailLog queryset based on request GET parameters.
    """
    status_filter = request_get_params.get('status', '').strip()
    event_title_filter = request_get_params.get('event__title__icontains', '').strip()

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if event_title_filter:
        queryset = queryset.filter(event__title__icontains=event_title_filter)

    ordering = request_get_params.get('ordering', '-sent_at')
    allowed_ordering_fields = [
        'sent_at', '-sent_at', 'subject', '-subject',
        'status', '-status', 'num_recipients', '-num_recipients',
        'num_sent_successfully', '-num_sent_successfully',
        'sent_by__email', '-sent_by__email', 'event__title', '-event__title'
    ]
    if ordering in allowed_ordering_fields:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('-sent_at')

    return queryset


def filter_and_sort_utm_records(queryset, request_get_params):
    """
    Applies search, filters, and ordering to a UTMData queryset based on request GET parameters.
    """
    search_query = request_get_params.get('q', '').strip()
    filter_source = request_get_params.get('source', '').strip()
    filter_medium = request_get_params.get('medium', '').strip()
    filter_campaign = request_get_params.get('campaign', '').strip()
    filter_role = request_get_params.get('role', '').strip()

    if search_query:
        queryset = queryset.filter(
            Q(user__email__icontains=search_query) |
            Q(event__title__icontains=search_query) |
            Q(utm_source__icontains=search_query) |
            Q(utm_medium__icontains=search_query) |
            Q(utm_campaign__icontains=search_query) |
            Q(utm_term__icontains=search_query) |
            Q(utm_content__icontains=search_query) |
            Q(session_id__icontains=search_query)
        )

    if filter_source:
        queryset = queryset.filter(utm_source__iexact=filter_source)
    if filter_medium:
        queryset = queryset.filter(utm_medium__iexact=filter_medium)
    if filter_campaign:
        queryset = queryset.filter(utm_campaign__iexact=filter_campaign)
    if filter_role:
        queryset = queryset.filter(role_change_type__iexact=filter_role)

    sort_by = request_get_params.get('sort', '-timestamp')
    valid_sort_fields = [
        'timestamp', '-timestamp',
        'user__email', '-user__email',
        'event__title', '-event__title',
        'role_change_type', '-role_change_type',
        'utm_source', '-utm_source',
        'utm_medium', '-utm_medium',
        'utm_campaign', '-utm_campaign',
        'utm_term', '-utm_term',
        'utm_content', '-utm_content',
        'session_id', '-session_id',
    ]
    if sort_by in valid_sort_fields:
        queryset = queryset.order_by(sort_by)
    else:
        sort_by = '-timestamp'
        queryset = queryset.order_by(sort_by)

    return queryset, sort_by


def manage_event_user_role(event: Event, user: CustomUser, desired_is_host: bool,
                           desired_is_attend: bool) -> dict:
    """
    Manages a user's role (host or attendee) for a given event.
    Handles adding/removing users from roles and enforces capacity limits.
    Returns a dictionary with success status, messages, HTTP status code,
    whether a change was performed, the type of change, and the user's current status.
    """
    messages = []
    status_code = 200  # Mặc định là OK
    actual_role_change_performed = False
    final_role_change_type = None

    current_is_hosting = event.hosts.filter(pk=user.pk).exists()
    current_is_attending = event.attendees.filter(pk=user.pk).exists()

    if desired_is_host and desired_is_attend:
        messages.append(
            "A user cannot be both a Host and an Attendee simultaneously. Please select only one role.")
        return {
            'success': False,
            'messages': messages,
            'status_code': 400,
            'actual_role_change_performed': False,
            'final_role_change_type': None,
            'current_status': {
                'is_hosting': current_is_hosting,
                'is_attending': current_is_attending
            }
        }

    # Đảm bảo tất cả các thao tác thay đổi vai trò diễn ra trong một transaction nguyên tử
    with transaction.atomic():
        # Xử lý vai trò Host
        if desired_is_host:
            if not current_is_hosting:
                event.hosts.add(user)
                messages.append(f"'{user.email}' has been added as a Host.")
                actual_role_change_performed = True
                final_role_change_type = 'host'
            else:
                messages.append(f"'{user.email}' is already a Host.")

            # Nếu người dùng đang là Attendee, hãy loại bỏ họ khỏi Attendee
            if current_is_attending:
                event.attendees.remove(user)
                messages.append(
                    f"'{user.email}' has been removed from Attendees (as they are now a Host).")
                actual_role_change_performed = True
        elif not desired_is_host and current_is_hosting:
            # Nếu không muốn là host nữa nhưng hiện tại đang là host, thì loại bỏ
            event.hosts.remove(user)
            messages.append(f"'{user.email}' has been removed from Hosts.")
            actual_role_change_performed = True
            final_role_change_type = 'unregistered'  # Hoặc 'unhost' rõ ràng hơn

        # Kiểm tra lại trạng thái host sau khi xử lý host, để quyết định xử lý attendee
        user_is_host_after_host_processing = event.hosts.filter(pk=user.pk).exists()

        # Xử lý vai trò Attendee (chỉ khi người dùng không phải là Host)
        if not user_is_host_after_host_processing:
            if desired_is_attend:
                if not current_is_attending:
                    # Kiểm tra sức chứa trước khi thêm attendee
                    if event.max_capacity and event.attendees.count() >= event.max_capacity:
                        messages.append(f"Event is full, cannot add '{user.email}' as an Attendee.")
                        status_code = 400  # Đặt trạng thái lỗi do sức chứa
                        actual_role_change_performed = False  # Không có thay đổi nào được thực hiện
                    else:
                        event.attendees.add(user)
                        messages.append(f"'{user.email}' has been added as an Attendee.")
                        actual_role_change_performed = True
                        final_role_change_type = 'attendee'
                else:
                    messages.append(f"'{user.email}' is already an Attendee.")
            elif not desired_is_attend and current_is_attending:
                # Nếu không muốn là attendee nữa nhưng hiện tại đang là attendee, thì loại bỏ
                event.attendees.remove(user)
                messages.append(f"'{user.email}' has been removed from Attendees.")
                actual_role_change_performed = True
                if final_role_change_type is None:  # Chỉ đặt nếu chưa được đặt từ logic host
                    final_role_change_type = 'unregistered'  # Hoặc 'unattend' rõ ràng hơn

        # Lưu sự kiện sau khi tất cả các thay đổi trong transaction đã được thực hiện
        event.save()

    # Nếu không có thay đổi nào được thực hiện và không có tin nhắn nào được thêm
    if not actual_role_change_performed and not messages:
        messages.append("No changes were made to user's roles.")

    # Cập nhật trạng thái cuối cùng của người dùng sau khi thay đổi
    current_status = {
        'is_hosting': event.hosts.filter(pk=user.pk).exists(),
        'is_attending': event.attendees.filter(pk=user.pk).exists()
    }

    return {
        'success': status_code == 200 and actual_role_change_performed,
        'messages': messages,
        'status_code': status_code,
        'actual_role_change_performed': actual_role_change_performed,
        'final_role_change_type': final_role_change_type,
        'current_status': current_status
    }


def record_utm_data_for_event_role_change(user: CustomUser, event: Event, role_change_type: str,
                                          utm_data_fields: dict) -> dict:
    """
    Records UTM data for a user's role change related to an event.
    Returns a dictionary with success status and a message.
    """
    try:
        utm_record_payload = {
            **utm_data_fields,
            'user': user,
            'event': event,
            'role_change_type': role_change_type
        }
        UTMData.objects.create(**utm_record_payload)
        message = f"UTM data recorded for role change: '{role_change_type}'."
        logger.info(
            f"UTM data created for {user.email} (Event: {event.slug}, Role: {role_change_type}). Data: {utm_record_payload}")
        return {'success': True, 'message': message}
    except Exception as e:
        message = f"Failed to record UTM data: {e}."
        logger.error(f"Error creating UTMData for {user.email}: {e}")
        return {'success': False, 'message': message}
