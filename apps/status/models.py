from django.conf import settings
from django.db import models


class StatusUpdate(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="status_updates",
        limit_choices_to={"role": "student"},
    )
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    # simple counters (no realtime yet)
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.created_at}"
