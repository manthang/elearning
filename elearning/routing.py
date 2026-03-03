# elearning/routing.py

from channels.routing import URLRouter
from django.urls import path
from apps.chat import routing as chat_routing
from apps.notifications import routing as notification_routing # If you created this

websocket_urlpatterns = [
    # Include all paths from the chat app
    path('', URLRouter(chat_routing.websocket_urlpatterns)),
    
    # Include all paths from the notification app
    path('', URLRouter(notification_routing.websocket_urlpatterns)),
]
