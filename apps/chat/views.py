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
def chat_history(request, user_id):
    convo = (
        Conversation.objects
        .filter(participants=request.user)
        .filter(participants=user_id)
        .first()
    )

    if not convo:
        return JsonResponse({"messages": []})

    messages = [
        {
            "sender": m.sender.id,
            "content": m.content,
            "time": m.created_at.strftime("%H:%M"),
        }
        for m in convo.messages.order_by("created_at")
    ]

    return JsonResponse({"messages": messages})


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
