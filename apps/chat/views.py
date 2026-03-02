import json
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

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
        other = convo.participants.exclude(id=request.user.id).first()
        if not other:
            # Edge case: convo with only yourself (shouldn't happen, but avoid crashing)
            continue

        last_message = (
            Message.objects
            .filter(conversation=convo)
            .order_by("-created_at")
            .first()
        )

        data.append({
            "id": convo.id,
            "user_id": other.id,
            "name": other.full_name or other.username,
            "role": getattr(other, "role", ""),
            "avatar_url": other.avatar_url,
            "last_message": last_message.content if last_message else "",
            "sender_id": last_message.sender_id if last_message else None,  # ADD THIS
            "time": last_message.created_at.strftime("%H:%M") if last_message else "",
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

    # Exclude messages cleared by the current user
    messages = conversation.messages.exclude(cleared_by=request.user).order_by('created_at')

    return JsonResponse({
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "sender_id": msg.sender_id,
                "created_at": msg.created_at.strftime("%H:%M"),
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

    return JsonResponse({
        "conversation_id": conversation.id,
        "id": other_user.id,
        "name": other_user.full_name or other_user.username,
        "role": other_user.get_role_display() if hasattr(other_user, 'get_role_display') else "",
        "avatar_url": other_user.avatar_url, 
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
def block_user(request, user_id):
    """Blocks a user, preventing them from sending messages to the requesting user."""
    user_to_block = get_object_or_404(User, id=user_id)
    
    if request.user == user_to_block:
        return JsonResponse({"error": "You cannot block yourself."}, status=400)

    # Create the block relationship
    UserBlock.objects.get_or_create(blocker=request.user, blocked=user_to_block)
    
    return JsonResponse({"success": True, "message": f"You have blocked {user_to_block.full_name or user_to_block.username}."})
