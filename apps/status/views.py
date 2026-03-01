from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import *
from .forms import *


@login_required
@require_POST
def post_status(request):
    form = StatusUpdateForm(request.POST)
    
    # Grab the intended redirect URL
    next_url = request.POST.get("next") or request.META.get('HTTP_REFERER') or reverse("core:home")

    # Prevent Open Redirect Attacks
    # Ensures a malicious user hasn't manipulated the 'next' hidden input to bounce users to a scam site
    url_is_safe = url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    if not url_is_safe:
        next_url = reverse("core:home")

    # Guarantee they land back on the status tab
    if "?tab=status" not in next_url:
        # Append it so the page doesn't flip back to the overview tab after posting
        separator = "&" if "?" in next_url else "?"
        next_url = f"{next_url}{separator}tab=status"

    if form.is_valid():
        status = form.save(commit=False)
        status.author = request.user
        status.save()
        messages.success(request, "Update posted successfully!")
    else:
        # Show actual form errors instead of a generic message
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect(next_url)


@login_required
@require_POST
def toggle_like(request, status_id):
    status = get_object_or_404(StatusUpdate, id=status_id)
    
    # Check if a Like object exists for this user and post
    like = Like.objects.filter(status_update=status, user=request.user).first()
    
    if like:
        like.delete() # Unlike
    else:
        Like.objects.create(status_update=status, user=request.user) # Like
    
    next_url = request.META.get('HTTP_REFERER') or reverse("courses:student_home")
    return redirect(next_url)


@login_required
@require_POST
def delete_status(request, status_id):
    # 1. Fetch the status or 404
    status = get_object_or_404(StatusUpdate, id=status_id)

    # 2. Security Check: Only the author can delete their own post
    # (Optional: allow teachers/admins to delete anything by adding 'or request.user.is_teacher')
    if status.author != request.user:
        return HttpResponseForbidden("You do not have permission to delete this post.")

    # 3. Perform the deletion
    status.delete()
    messages.success(request, "Post deleted successfully.")

    # 4. Determine Redirect URL (Stay on current page)
    next_url = request.POST.get("next") or request.META.get('HTTP_REFERER')
    
    # Fallback to home if no referer is found
    if not next_url:
        next_url = reverse("courses:student_home") + "?tab=status"

    return redirect(next_url)


@login_required
@require_POST
def post_comment(request, status_id):
    status = get_object_or_404(StatusUpdate, id=status_id)
    content = request.POST.get("content", "").strip()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not content:
        if is_ajax:
            return JsonResponse({"success": False, "error": "Comment cannot be empty."}, status=400)
        messages.error(request, "Comment cannot be empty.")
        return redirect(request.META.get('HTTP_REFERER', reverse("core:home")))

    # Save the comment
    comment = Comment.objects.create(
        status_update=status,
        author=request.user,
        content=content
    )

    # If it's an AJAX request, return the data as JSON to inject into the page
    if is_ajax:
        return JsonResponse({
            "success": True,
            "comment_id": comment.id,
            "author_name": request.user.first_name or request.user.username,
            "avatar_url": request.user.avatar_url if hasattr(request.user, 'avatar_url') else '',
            "content": comment.content,
            "time": "Just now"
        })

    # Standard fallback for users with JS disabled
    next_url = request.POST.get("next") or request.META.get('HTTP_REFERER') or reverse("core:home")
    if "?tab=status" not in next_url:
        separator = "&" if "?" in next_url else "?"
        next_url = f"{next_url}{separator}tab=status"
        
    messages.success(request, "Comment posted!")
    return redirect(next_url)


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    status_id = comment.status_update.id

    # Security check: Only the author can delete it
    if comment.author != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "error": "Unauthorized"}, status=403)
        return HttpResponseForbidden("You cannot delete this comment.")

    # Delete the comment
    comment.delete()

    # If it's an AJAX background request, return a success JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"success": True})

    # Standard fallback
    messages.success(request, "Comment deleted.")
    next_url = request.POST.get("next") or request.META.get('HTTP_REFERER') or reverse("core:home")
    return redirect(next_url)