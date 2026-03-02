from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("conversations/", views.conversation_list, name="conversation_list"),
    path("start/<int:user_id>/", views.start_conversation, name="start_conversation"),
    path("history/<int:conversation_id>/", views.chat_history, name="chat_history"),
    path('clear/<int:conversation_id>/', views.clear_chat, name='clear_chat'),
    path('block/<int:conversation_id>/', views.block_user, name='block_user'),
]
