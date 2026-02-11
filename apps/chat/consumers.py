import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from .models import Conversation, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.target_user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_name = self.get_room_name(self.user.id, self.target_user_id)
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        print("🔥 WebSocket connect called")
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        conversation = await self.get_or_create_conversation(
            self.user.id,
            self.target_user_id
        )

        msg = await self.save_message(conversation, self.user, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": msg.content,
                "sender_id": self.user.id,
                "timestamp": msg.created_at.strftime("%H:%M"),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    def get_room_name(self, u1, u2):
        return "_".join(sorted([str(u1), str(u2)]))

    @database_sync_to_async
    def get_or_create_conversation(self, u1, u2):
        qs = Conversation.objects.filter(participants=u1).filter(participants=u2)
        if qs.exists():
            return qs.first()

        convo = Conversation.objects.create()
        convo.participants.add(u1, u2)
        return convo

    @database_sync_to_async
    def save_message(self, conversation, sender, content):
        return Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content
        )
