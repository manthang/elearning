from django.conf import settings
from django.db import models

class StatusUpdate(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="status_updates"
    )
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # NEW: Proper Like system (Many-to-Many is better than a simple IntegerField)
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="liked_statuses", 
        blank=True
    )

    # NEW: Support for pinned announcements by instructors
    is_pinned = models.BooleanField(default=False)
    
    # NEW: Threaded replies (a status can be a reply to another status)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies'
    )

    class Meta:
        ordering = ["-is_pinned", "-created_at"] # Pinned posts always stay at the top

    @property
    def likes_count(self):
        return self.liked_by.count()

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}..."
