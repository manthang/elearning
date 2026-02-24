# notifications/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from .models import Notification

@login_required
def notifications_list(request):
    qs = request.user.notifications.all()[:50]
    return render(request, "notifications/list.html", {"notifications": qs})

@login_required
def notification_mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return redirect(n.url or "notifications:list")

@login_required
def notifications_mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:list")