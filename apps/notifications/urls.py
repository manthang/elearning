# notifications/urls.py
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notifications_list, name="list"),
    path("mark-all-read/", views.notifications_mark_all_read, name="mark_all_read"),
    path("<int:pk>/read/", views.notification_mark_read, name="mark_read"),
]