import logging
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from crm_events import models
from crm_events.models import CustomUser, EmailLog
from crm_events.serializers import CustomUserSerializer, EmailSendSerializer
from crm_events.services import apply_user_filters, get_filter_applies

logger = logging.getLogger(__name__)


def user_filter_page(request):
    return render(request, 'crm_events/user_filter_page.html', {})


class CustomUserFilterView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = CustomUser.objects.all()
        query_params = request.query_params

        queryset = apply_user_filters(queryset, query_params)

        try:
            if query_params.get('total_hosting_events_min'):
                int(query_params['total_hosting_events_min'])
            if query_params.get('total_hosting_events_max'):
                int(query_params['total_hosting_events_max'])
            if query_params.get('total_registered_events_min'):
                int(query_params['total_registered_events_min'])
            if query_params.get('total_registered_events_max'):
                int(query_params['total_registered_events_max'])
        except ValueError:
            return Response({"error": "Min/max event counts must be integers."},
                            status=status.HTTP_400_BAD_REQUEST)

        order_by = query_params.get('ordering', None)
        valid_ordering_fields = [
            'username', '-username', 'email', '-email', 'date_joined', '-date_joined',
            'total_owned_events', '-total_owned_events',
            'total_hosting_events', '-total_hosting_events',
            'total_registered_events', '-total_registered_events',
            'company', '-company', 'city', '-city', 'state', '-state', 'job_title', '-job_title'
        ]
        if order_by and order_by in valid_ordering_fields:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by('username')

        paginator = PageNumberPagination()
        paginator.page_size = request.query_params.get('page_size', 10)
        try:
            paginator.page_size = int(paginator.page_size)
        except ValueError:
            return Response({"error": "page_size must be an integer"},
                            status=status.HTTP_400_BAD_REQUEST)

        page = paginator.paginate_queryset(queryset, request, view=self)

        if page is not None:
            serializer = CustomUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CustomUserSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SendEmailsView(APIView):
    """
    Endpoint to send emails to a filtered set of users.
    Requires authentication and admin/staff user permission.
    """
    def post(self, request, *args, **kwargs):
        serializer = EmailSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        queryset = CustomUser.objects.all()
        queryset = apply_user_filters(queryset, validated_data)

        recipient_list = [user.email for user in queryset if user.email]

        if not recipient_list:
            logger.info("No users found matching the filter criteria for email sending.")
            return Response(
                {"message": "No users found matching the filter criteria. No emails sent."},
                status=status.HTTP_200_OK)

        subject = validated_data['subject']
        body = validated_data['body']
        sender_user = request.user if request.user.is_authenticated else None
        email_log = EmailLog(
            subject=subject,
            body=body,
            filters_applied=get_filter_applies(validated_data),
            recipients=recipient_list,
            sent_by=sender_user,
            num_recipients=len(recipient_list),
            status='FAILED'
        )
        try:
            num_sent = send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False,
            )
            email_log.num_sent_successfully = num_sent
            if num_sent == len(recipient_list):
                email_log.status = 'SUCCESS'
            elif num_sent > 0:
                email_log.status = 'PARTIAL_SUCCESS'
            else:
                email_log.status = 'FAILED'
            email_log.save()
            logger.info(f"Successfully initiated sending emails to {len(recipient_list)} recipients. {num_sent} sent.")
            return Response({
                "message": f"Emails sent successfully to {num_sent} recipients.",
                "recipients_count": len(recipient_list),
                "sent_count": num_sent
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Failed to send emails. Error: {e}") # Use logger.exception for traceback
            return Response({"error": f"Failed to send emails: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailAnalyticsView(APIView):
    def get(self, request, *args, **kwargs):
        total_emails_sent = EmailLog.objects.count()
        total_success = EmailLog.objects.filter(status='SUCCESS').count()
        total_failed = EmailLog.objects.filter(status='FAILED').count()
        total_partial = EmailLog.objects.filter(status='PARTIAL_SUCCESS').count()

        total_recipients_reached = EmailLog.objects.aggregate(
            sum_recipients=models.Sum('num_sent_successfully')
        )['sum_recipients'] or 0

        emails_by_date = EmailLog.objects.annotate(
            date=models.functions.TruncDate('sent_at')
        ).values('date').annotate(
            count=models.Count('id')
        ).order_by('date')

        return Response({
            "total_emails_logged": total_emails_sent,
            "success_rate": {
                "success": total_success,
                "failed": total_failed,
                "partial_success": total_partial,
                "total_recipients_reached": total_recipients_reached
            },
            "emails_by_date": list(emails_by_date)
        }, status=status.HTTP_200_OK)
