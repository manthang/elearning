import json
from django.utils import timezone
from django.db.models import Q
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import *

User = get_user_model()

class InboxConsumer(AsyncWebsocketConsumer):
    """
    Single socket per user.
    - Joins: user_<user_id>
    - Client sends: { "type": "send", "conversation_id": 123, "message": "hi" }
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

            # Ensure user is actually in this chat
            allowed = await self.user_in_conversation(conversation_id)
            if not allowed:
                return

            # Security Check: Are these users blocking each other?
            is_blocked = await self.check_if_blocked(conversation_id)
            if is_blocked:
                # Silently reject, or send an error back to the sender
                await self.send(text_data=json.dumps({
                    "error": "You cannot send messages to this user.",
                    "conversation_id": conversation_id
                }))
                return

            # 3. Save to database
            msg_obj = await self.save_message(conversation_id, message)
            participant_ids = await self.get_participant_ids(conversation_id)

            payload = {
                "type": "inbox_message",
                "conversation_id": conversation_id,
                "message_id": msg_obj["id"],
                "message": msg_obj["content"],
                "sender_id": msg_obj["sender_id"],
                "created_at": msg_obj["created_at"],  # Now formatted as "HH:MM AM/PM"
            }

            # 4. Broadcast to each participant's inbox group
            for uid in participant_ids:
                await self.channel_layer.group_send(f"user_{uid}", payload)

    async def inbox_message(self, event):
        # Forward the broadcast payload to the user's browser
        await self.send(text_data=json.dumps({
            "conversation_id": event["conversation_id"],
            "message_id": event["message_id"],
            "message": event["message"],
            "sender_id": event["sender_id"],
            "created_at": event.get("created_at", ""),
        }))

    async def live_notification(self, event):
        """
        Catches the signal from Django and forwards it to the client's browser.
        """
        await self.send(text_data=json.dumps({
            "type": "notification",
            "payload": event["payload"]
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
    def check_if_blocked(self, conversation_id):
        """Check bidirectional block status between participants."""
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            other_user = conversation.participants.exclude(id=self.user.id).first()
            
            if not other_user:
                return False

            if other_user:
                return UserBlock.objects.filter(
                    Q(blocker=self.user, blocked=other_user) |
                    Q(blocker=other_user, blocked=self.user)
                ).exists()
        except Conversation.DoesNotExist:
            pass
        return False

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

        # Update the parent conversation's timestamp
        convo.updated_at = timezone.now()
        convo.save(update_fields=["updated_at"])

        return {
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "created_at": msg.created_at.strftime("%I:%M %p"), # 12-hour format
        }