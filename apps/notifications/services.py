# notifications/services.py
from .models import Notification

def notify(*, recipient, title, verb, message="", url="", actor=None, course=None):
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        course=course,
        verb=verb,
        title=title,
        message=message,
        url=url,
    )