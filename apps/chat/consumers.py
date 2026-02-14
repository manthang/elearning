import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class InboxConsumer(AsyncWebsocketConsumer):
    """
    Single socket per user.
    - Joins: user_<user_id>
    - Client sends: { "type": "send", "conversation_id": 123, "message": "hi" }
    - Server broadcasts to BOTH participants via their user groups:
        {conversation_id, message_id, message, sender_id, created_at}
    """

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        if msg_type == "send":
            conversation_id = data.get("conversation_id")
            message = (data.get("message") or "").strip()
            if not conversation_id or not message:
                return

            allowed = await self.user_in_conversation(conversation_id)
            if not allowed:
                # Don't leak anything
                return

            msg_obj = await self.save_message(conversation_id, message)

            participant_ids = await self.get_participant_ids(conversation_id)

            payload = {
                "type": "inbox_message",
                "conversation_id": conversation_id,
                "message_id": msg_obj["id"],
                "message": msg_obj["content"],
                "sender_id": msg_obj["sender_id"],
                "created_at": msg_obj["created_at"],  # "HH:MM"
            }

            # Broadcast to each participant's inbox group
            for uid in participant_ids:
                await self.channel_layer.group_send(f"user_{uid}", payload)

    async def inbox_message(self, event):
        # Just forward to browser
        await self.send(text_data=json.dumps({
            "conversation_id": event["conversation_id"],
            "message_id": event["message_id"],
            "message": event["message"],
            "sender_id": event["sender_id"],
            "created_at": event.get("created_at", ""),
        }))

    # -------------------------
    # DB helpers
    # -------------------------
    @database_sync_to_async
    def user_in_conversation(self, conversation_id):
        return Conversation.objects.filter(
            id=conversation_id,
            participants=self.user
        ).exists()

    @database_sync_to_async
    def get_participant_ids(self, conversation_id):
        return list(
            Conversation.objects.get(id=conversation_id)
            .participants.values_list("id", flat=True)
        )

    @database_sync_to_async
    def save_message(self, conversation_id, content):
        convo = Conversation.objects.get(id=conversation_id)

        msg = Message.objects.create(
            conversation=convo,
            sender=self.user,
            content=content
        )

        # IMPORTANT: keep conversation ordering correct
        convo.updated_at = timezone.now()
        convo.save(update_fields=["updated_at"])

        return {
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "created_at": msg.created_at.strftime("%H:%M"),
        }


class ChatConsumer(AsyncWebsocketConsumer):
    """
    (Optional legacy) Conversation-scoped socket.
    If you keep using it, at least update convo.updated_at when saving.
    """

    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"

        is_valid = await self.user_in_conversation()
        if not is_valid:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = (data.get("message") or "").strip()
        if not message:
            return

        msg_obj = await self.save_message(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "conversation_id": int(self.conversation_id),
                "message_id": msg_obj["id"],
                "message": msg_obj["content"],
                "sender_id": msg_obj["sender_id"],
                "created_at": msg_obj["created_at"],
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "conversation_id": event["conversation_id"],
            "message_id": event["message_id"],
            "message": event["message"],
            "sender_id": event["sender_id"],
            "created_at": event.get("created_at", ""),
        }))

    @database_sync_to_async
    def user_in_conversation(self):
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user
        ).exists()

    @database_sync_to_async
    def save_message(self, content):
        from django.utils import timezone

        conversation = Conversation.objects.get(id=self.conversation_id)
        msg = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content
        )

        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])

        return {
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "created_at": msg.created_at.strftime("%H:%M"),
        }
