from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import *


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
            "conversation_id": convo.id,
            "user_id": other.id,
            "name": other.full_name or other.username,
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
