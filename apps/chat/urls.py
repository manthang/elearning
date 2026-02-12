from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("history/<int:user_id>/", views.chat_history, name="chat_history"),
    path("conversations/", views.conversation_list, name="conversation_list"),
]
