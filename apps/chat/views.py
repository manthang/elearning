import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .models import *

# Get the actual Model class, not the string
User = get_user_model()


@login_required
def conversation_list(request):
    conversations = (
        Conversation.objects
        .filter(participants=request.user)
        .prefetch_related("participants")
        .order_by("-updated_at")
    )

    data = []
    for convo in conversations:
        other_user = convo.participants.exclude(id=request.user.id).first()
        if not other_user:
            # Edge case: convo with only yourself (shouldn't happen, but avoid crashing)
            continue

        # 1. Did the currently logged-in user block the other person?
        i_blocked_them = False
        # 2. Did the other person block the currently logged-in user?
        they_blocked_me = False

        if other_user:
            i_blocked_them = UserBlock.objects.filter(blocker=request.user, blocked=other_user).exists()
            they_blocked_me = UserBlock.objects.filter(blocker=other_user, blocked=request.user).exists()

        last_message = (
            Message.objects
            .filter(conversation=convo)
            .order_by("-created_at")
            .first()
        )

        data.append({
            "id": convo.id,
            "user_id": other_user.id,
            "name": other_user.full_name or other_user.username,
            "username": other_user.username,
            "role": getattr(other_user, "role", ""),
            "avatar_url": other_user.avatar_url,
            "last_message": last_message.content if last_message else "",
            "sender_id": last_message.sender_id if last_message else None,
            "time": last_message.created_at.strftime("%H:%M") if last_message else "",
            "i_blocked_them": i_blocked_them,
            "they_blocked_me": they_blocked_me,
        })

    return JsonResponse({"conversations": data})


@login_required
def chat_history(request, conversation_id):
    try:
        conversation = Conversation.objects.get(
            id=conversation_id,
            participants=request.user
        )
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "Invalid conversation"}, status=403)

    # Find the other user in this conversation first
    other_user = conversation.participants.exclude(id=request.user.id).first()

    # Exclude messages cleared by the current user
    messages = conversation.messages.exclude(cleared_by=request.user).order_by('created_at')

    # Did the currently logged-in user block the other person?
    i_blocked_them = False
    # Did the other person block the currently logged-in user?
    they_blocked_me = False

    if other_user:
        i_blocked_them = UserBlock.objects.filter(blocker=request.user, blocked=other_user).exists()
        they_blocked_me = UserBlock.objects.filter(blocker=other_user, blocked=request.user).exists()

    return JsonResponse({
        # Actually send the block status to your JavaScript
        "i_blocked_them": i_blocked_them,
        "they_blocked_me": they_blocked_me,
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "sender_id": msg.sender_id,
                # Updated to "%I:%M %p" (e.g., 03:30 PM) to match your updated consumers.py
                "created_at": msg.created_at.strftime("%I:%M %p"),
            }
            for msg in messages
        ]
    })


# ========================
# Start a Chat with a User
# ========================
@login_required
def start_conversation(request, user_id):
    current_user = request.user
    other_user = get_object_or_404(User, id=user_id)

    if current_user == other_user:
        return JsonResponse({"error": "Cannot start a conversation with yourself."}, status=400)

    # Find an existing conversation between exactly these two participants
    conversation = (
        Conversation.objects
        .filter(participants=current_user)
        .filter(participants=other_user)
        .distinct()
        .first()
    )

    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(current_user, other_user)

    # 1. Did the currently logged-in user block the other person?
    i_blocked_them = False
    # 2. Did the other person block the currently logged-in user?
    they_blocked_me = False

    if other_user:
        i_blocked_them = UserBlock.objects.filter(blocker=request.user, blocked=other_user).exists()
        they_blocked_me = UserBlock.objects.filter(blocker=other_user, blocked=request.user).exists()

    return JsonResponse({
        "conversation_id": conversation.id,
        "id": other_user.id,
        "name": other_user.full_name or other_user.username,
        "username": other_user.username,
        "role": other_user.get_role_display() if hasattr(other_user, 'get_role_display') else "",
        "avatar_url": other_user.avatar_url,
        "i_blocked_them": i_blocked_them,
        "they_blocked_me": they_blocked_me,
    })


@login_required
@require_POST
def clear_chat(request, conversation_id):
    """Hides all current messages in a conversation for the requesting user."""
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    
    # Get all messages currently in this conversation
    messages = conversation.messages.exclude(cleared_by=request.user)
    
    # Add the current user to the 'cleared_by' field for all these messages
    for msg in messages:
        msg.cleared_by.add(request.user)
        
    return JsonResponse({"success": True, "message": "Chat history cleared."})


@login_required
@require_POST
def block_user(request, conversation_id):
    """Blocks the other participant in a given conversation."""
    # Fetch the conversation
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    
    # Find the other user in this chat
    user_to_block = conversation.participants.exclude(id=request.user.id).first()
    
    if not user_to_block:
        return JsonResponse({"error": "Could not find the user to block."}, status=404)

    # Create the block relationship
    UserBlock.objects.get_or_create(blocker=request.user, blocked=user_to_block)
    
    return JsonResponse({
        "success": True, 
        "message": f"You have blocked {user_to_block.full_name or user_to_block.username}."
    })
