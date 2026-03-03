# apps/chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # One inbox socket per logged-in user
    re_path(r"^ws/chat/inbox/$", consumers.InboxConsumer.as_asgi()),
]
