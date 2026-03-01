from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from apps.accounts.models import User


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
            "avatar": other.profile_photo.url if getattr(other, "profile_photo", None) else "",
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

    messages = Message.objects.filter(conversation=conversation).order_by("created_at")

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
        "avatar": other_user.avatar_url, 
    })
