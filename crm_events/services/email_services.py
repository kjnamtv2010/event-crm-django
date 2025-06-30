import json
import logging

from django.db import transaction
from django.urls import reverse
from urllib.parse import urlencode

from config.settings import TIMEZONE
from crm_events.models import Event, EmailLog
from crm_events.token_utils import generate_event_token
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def build_event_email_with_encrypted_link(event_obj, request_obj, user_email, user_id):
    event_obj.refresh_from_db()
    event_slug = event_obj.slug
    current_host = request_obj.get_host()
    scheme = 'https' if request_obj.is_secure() else 'http'
    base_domain_with_scheme = f"{scheme}://{current_host}"
    event_page_path = reverse('event-detail-page', kwargs={'slug': event_slug})
    base_url = base_domain_with_scheme.rstrip('/') + event_page_path

    utm_params = {
        'utm_source': "crm_email",
        'utm_medium': "email",
        'utm_campaign': f"event_{event_slug.replace('-', '_')}",
        'utm_content': "textlink"
    }
    event_expiry_datetime = event_obj.end_at
    if event_expiry_datetime.tzinfo is None:
        event_expiry_datetime = TIMEZONE.localize(event_expiry_datetime)
    else:
        event_expiry_datetime = event_expiry_datetime.astimezone(TIMEZONE)

    encrypted_token_param = generate_event_token(user_email, user_id, event_expiry_datetime)

    all_query_params = {**utm_params, 'token': encrypted_token_param}
    final_event_link = f"{base_url}?{urlencode(all_query_params)}"
    return final_event_link


@transaction.atomic
def send_bulk_event_emails(subject, body_template, users, event_slug=None, sender_user=None, filters_applied=None, request=None):
    event_obj = None
    if event_slug:
        try:
            event_obj = Event.objects.get(slug=event_slug)
        except Event.DoesNotExist:
            raise ValueError("Event not found.")

    email_log = EmailLog.objects.create(
        subject=subject,
        body=body_template,
        filters_applied=filters_applied or {},
        recipients=json.dumps([user.email for user in users]),
        sent_by=sender_user,
        num_recipients=len(users),
        status='PENDING',
        event=event_obj
    )

    num_success = 0

    for user in users:
        try:
            body_content = body_template
            if event_obj:
                final_event_link = build_event_email_with_encrypted_link(
                    event_obj, request, user.email, user.id
                )
                if '{event_link}' in body_content:
                    body_content = body_content.replace('{event_link}', final_event_link)
                else:
                    body_content += f"\n\nMore info: {final_event_link}"

            send_mail(
                subject=subject,
                message=body_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            num_success += 1
        except Exception as e:
            logger.exception(f"Failed to send to {user.email}: {e}")

    email_log.num_sent_successfully = num_success
    email_log.status = (
        'SUCCESS' if num_success == len(users)
        else 'PARTIAL_SUCCESS' if num_success > 0
        else 'FAILED'
    )
    email_log.save()

    return num_success, len(users)
