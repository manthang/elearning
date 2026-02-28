from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from .models import *
from .forms import *


@login_required
@require_POST
def post_status(request):
    form = StatusUpdateForm(request.POST)
    
    # Determine where to redirect back to
    next_url = request.POST.get("next") or request.META.get('HTTP_REFERER') or reverse("courses:student_home")

    if form.is_valid():
        status = form.save(commit=False)
        status.author = request.user
        status.save()
        messages.success(request, "Update posted to the community!")
    else:
        messages.error(request, "Could not post update. Please check your content.")

    return redirect(next_url)


@login_required
@require_POST
def toggle_like(request, status_id):
    status = get_object_or_404(StatusUpdate, id=status_id)
    if request.user in status.liked_by.all():
        status.liked_by.remove(request.user)
    else:
        status.liked_by.add(request.user)
    
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