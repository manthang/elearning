# apps/notifications/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Notification connections
    re_path(r"^ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
]