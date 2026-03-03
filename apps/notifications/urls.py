# notifications/urls.py
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path('api/notifications/', views.GetNotificationsAPI.as_view(), name='api_notifications'),
    path('api/notifications/<int:pk>/read/', views.MarkNotificationReadAPI.as_view(), name='api_mark_notification_read'),
    path('api/notifications/read-all/', views.MarkAllNotificationsReadAPI.as_view(), name='api_mark_all_read'),
    path('api/notifications/<int:pk>/unread/', views.MarkNotificationUnreadAPI.as_view(), name='api_unread_notification'),
    path('api/notifications/<int:pk>/delete/', views.DeleteNotificationAPI.as_view(), name='api_delete_notification'),
    
]
