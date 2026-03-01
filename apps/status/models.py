from django.db import models
from django.conf import settings

class StatusUpdate(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='status_updates')
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update by {self.author.username} at {self.created_at}"

class Comment(models.Model):
    status_update = models.ForeignKey(StatusUpdate, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='status_comments')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Oldest comments first, typical for feeds

class Like(models.Model):
    status_update = models.ForeignKey(StatusUpdate, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='status_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only like a specific update once
        constraints = [
            models.UniqueConstraint(fields=['status_update', 'user'], name='unique_status_like')
        ]