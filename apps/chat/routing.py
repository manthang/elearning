from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # One socket per conversation (optional / legacy)
    re_path(r"ws/chat/(?P<conversation_id>\d+)/$", consumers.ChatConsumer.as_asgi()),

    # ✅ NEW: One inbox socket per logged-in user
    re_path(r"ws/chat/inbox/$", consumers.InboxConsumer.as_asgi()),
]
