from django.urls import path

from crm_events import views

urlpatterns = [
    path('users/', views.CustomUserFilterView.as_view(), name='user-filter-list'),
    path('users-ui/', views.user_filter_page, name='user_filter_ui'),
    path('send-emails/', views.SendEmailsView.as_view(), name='send-emails'),
]