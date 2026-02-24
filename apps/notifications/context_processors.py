# notifications/context_processors.py
def notifications_unread_count(request):
    if not request.user.is_authenticated:
        return {"notifications_unread_count": 0}
    return {"notifications_unread_count": request.user.notifications.filter(is_read=False).count()}