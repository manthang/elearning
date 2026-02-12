from django.contrib import admin
from .models import Conversation, Message


# -----------------------------
# Message Inline (inside Conversation)
# -----------------------------

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "content", "created_at")
    can_delete = False
    ordering = ("-created_at",)


# -----------------------------
# Conversation Admin
# -----------------------------

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_participants",
        "message_count",
        "created_at",
    )

    search_fields = (
        "participants__username",
        "participants__full_name",
    )

    list_filter = ("created_at",)

    filter_horizontal = ("participants",)

    inlines = [MessageInline]

    ordering = ("-created_at",)

    def display_participants(self, obj):
        return ", ".join(
            user.full_name or user.username
            for user in obj.participants.all()
        )
    display_participants.short_description = "Participants"

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Messages"


# -----------------------------
# Message Admin
# -----------------------------

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender",
        "short_content",
        "created_at",
    )

    search_fields = (
        "sender__username",
        "sender__full_name",
        "content",
    )

    list_filter = ("created_at", "conversation")

    ordering = ("-created_at",)

    readonly_fields = ("conversation", "sender", "content", "created_at")

    def short_content(self, obj):
        return obj.content[:40] + "..." if len(obj.content) > 40 else obj.content
    short_content.short_description = "Message"
