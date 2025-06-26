from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count
from crm_events.models import CustomUser
from crm_events.serializers import CustomUserSerializer

def user_filter_page(request):
    return render(request, 'crm_events/user_filter_page.html', {})


class CustomUserFilterView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = CustomUser.objects.all()

        queryset = queryset.annotate(
            total_owned_events=Count('owned_events', distinct=True),
            total_hosting_events=Count('hosting_events', distinct=True),
            total_registered_events=Count('event_registrations', distinct=True)
        )

        query_params = request.query_params

        company = query_params.get('company', None)
        if company:
            queryset = queryset.filter(company__icontains=company)

        job_title = query_params.get('job_title', None)
        if job_title:
            queryset = queryset.filter(job_title__icontains=job_title)

        city = query_params.get('city', None)
        if city:
            queryset = queryset.filter(city__icontains=city)

        state = query_params.get('state', None)
        if state:
            queryset = queryset.filter(state__icontains=state)

        total_hosting_events_min = query_params.get('total_hosting_events_min', None)
        total_hosting_events_max = query_params.get('total_hosting_events_max', None)
        if total_hosting_events_min:
            try:
                queryset = queryset.filter(total_hosting_events__gte=int(total_hosting_events_min))
            except ValueError:
                return Response({"error": "total_hosting_events_min must be an integer"},
                                status=status.HTTP_400_BAD_REQUEST)
        if total_hosting_events_max:
            try:
                queryset = queryset.filter(total_hosting_events__lte=int(total_hosting_events_max))
            except ValueError:
                return Response({"error": "total_hosting_events_max must be an integer"},
                                status=status.HTTP_400_BAD_REQUEST)

        total_registered_events_min = query_params.get('total_registered_events_min', None)
        total_registered_events_max = query_params.get('total_registered_events_max', None)
        if total_registered_events_min:
            try:
                queryset = queryset.filter(
                    total_registered_events__gte=int(total_registered_events_min))
            except ValueError:
                return Response({"error": "total_registered_events_min must be an integer"},
                                status=status.HTTP_400_BAD_REQUEST)
        if total_registered_events_max:
            try:
                queryset = queryset.filter(
                    total_registered_events__lte=int(total_registered_events_max))
            except ValueError:
                return Response({"error": "total_registered_events_max must be an integer"},
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

        from rest_framework.pagination import PageNumberPagination
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
