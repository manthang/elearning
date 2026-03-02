# notifications/urls.py
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path('api/notifications/', views.UnreadNotificationsAPI.as_view(), name='api_notifications'),
    path('api/notifications/<int:pk>/read/', views.MarkNotificationReadAPI.as_view(), name='api_mark_notification_read'),
]
