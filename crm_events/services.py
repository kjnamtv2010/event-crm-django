from django.db.models import Count

def apply_user_filters(queryset, filters):
    """
    Helper function to apply common filters to the CustomUser queryset.
    """
    queryset = queryset.annotate(
        total_owned_events=Count('owned_events', distinct=True),
        total_hosting_events=Count('hosting_events', distinct=True),
        total_registered_events=Count('event_registrations', distinct=True)
    )

    if filters.get('company'):
        queryset = queryset.filter(company__icontains=filters['company'])
    if filters.get('job_title'):
        queryset = queryset.filter(job_title__icontains=filters['job_title'])
    if filters.get('city'):
        queryset = queryset.filter(city__icontains=filters['city'])
    if filters.get('state'):
        queryset = queryset.filter(state__icontains=filters['state'])

    if filters.get('total_hosting_events_min') is not None:
        queryset = queryset.filter(
            total_hosting_events__gte=filters['total_hosting_events_min'])
    if filters.get('total_hosting_events_max') is not None:
        queryset = queryset.filter(
            total_hosting_events__lte=filters['total_hosting_events_max'])

    if filters.get('total_registered_events_min') is not None:
        queryset = queryset.filter(
            total_registered_events__gte=filters['total_registered_events_min'])
    if filters.get('total_registered_events_max') is not None:
        queryset = queryset.filter(
            total_registered_events__lte=filters['total_registered_events_max'])

    return queryset
