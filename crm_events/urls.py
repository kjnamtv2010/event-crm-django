from django.urls import path
from crm_events import views

urlpatterns = [
    path('users/', views.CustomUserFilterView.as_view(), name='user-filter-api'),
    path('users-ui/', views.UserFilterPageView.as_view(), name='user-filter-ui'),
    path('events/', views.EventListView.as_view(), name='event-list-api'),
    path('send-emails/', views.SendEmailsView.as_view(), name='send-emails'),
    path('events/register/<slug:slug>/', views.EventDetailAndRegisterView.as_view()),
    path('events/<slug:slug>/', views.EventDetailPageView.as_view(), name='event-detail-page'),
    path('api/utm-analysis/', views.UTMAnalysisView.as_view(), name='utm-analysis-api'),
    path('email-tracker/', views.EmailTrackerTemplateView.as_view(), name='email-status-tracker'),
    path('api/email-logs/', views.email_log_json_view, name='email-log-api'),
]