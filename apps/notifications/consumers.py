from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # We assume the user is authenticated. 
        # For production, consider adding auth validation here.
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user_id = self.scope["user"].id
        self.group_name = f"user_{self.user_id}"

        # Join the user's specific notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group when disconnected
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # This catches the broadcast we set up in signals.py!
    async def live_notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "payload": event["payload"]
        }))