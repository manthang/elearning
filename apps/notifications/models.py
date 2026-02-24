# notifications/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    # optional: who caused it (student who enrolled, teacher who uploaded, etc.)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications_actor",
    )

    # optional: course context
    course = models.ForeignKey(
        "courses.Course",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    # message payload
    verb = models.CharField(max_length=80)             # "enrolled", "uploaded material"
    title = models.CharField(max_length=140)
    message = models.TextField(blank=True)

    # where to go when clicking notification
    url = models.CharField(max_length=255, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient} - {self.title}"