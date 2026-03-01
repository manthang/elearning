from django.db.models import Count, Exists, OuterRef, Value, BooleanField
from .models import *


def get_feed_queryset(target_user, requesting_user):
    # 1. Fetch updates authored ONLY by the profile owner
    qs = StatusUpdate.objects.filter(author=target_user).select_related('author').annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True)
    ).order_by('-created_at')

    # 2. Check if the *visitor* has liked these posts
    if requesting_user.is_authenticated:
        qs = qs.annotate(
            is_liked_by_me=Exists(
                Like.objects.filter(status_update=OuterRef('pk'), user=requesting_user)
            )
        )
    else:
        qs = qs.annotate(is_liked_by_me=Value(False, output_field=BooleanField()))

    qs = qs.prefetch_related('comments__author')
    
    return qs