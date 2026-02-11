from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Conversation

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
