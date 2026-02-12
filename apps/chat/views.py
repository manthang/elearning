from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import *
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
            "role": other.role,
            "avatar": other.profile_photo.url if other.profile_photo else "",
            "last_message": last_message.content if last_message else "",
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

    messages = Message.objects.filter(
        conversation=conversation
    ).order_by("created_at")

    data = {
        "messages": [
            {
                "content": msg.content,
                "sender_id": msg.sender_id,
                "created_at": msg.created_at.strftime("%H:%M"),
            }
            for msg in messages
        ]
    }

    return JsonResponse(data)


@login_required
def start_conversation(request, user_id):
    current_user = request.user
    other_user = get_object_or_404(User, id=user_id)

    # 🚫 Prevent chatting with yourself
    if current_user == other_user:
        return JsonResponse(
            {"error": "Cannot start a conversation with yourself."},
            status=400
        )

    # 🔍 Check if conversation already exists (both participants present)
    conversation = (
        Conversation.objects
        .filter(participants=current_user)
        .filter(participants=other_user)
        .first()
    )

    # ➕ If not exists, create new one
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(current_user, other_user)

    # 🎯 Return structured response
    return JsonResponse({
        "conversation_id": conversation.id,
        "name": other_user.full_name or other_user.username,
        "role": other_user.role,
        "avatar": (
            other_user.profile_photo.url
            if getattr(other_user, "profile_photo", None)
            else None
        ),
    })
