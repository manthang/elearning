from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.contrib import messages

@login_required
@require_POST
def profile_update(request):
    user = request.user

    next_url = request.POST.get("next")

    full_name = (request.POST.get("full_name") or "").strip()
    location = (request.POST.get("location") or "").strip()
    bio = (request.POST.get("bio") or "").strip()

    if not full_name:
        messages.error(request, "Full name is required.")
        # redirect back to wherever user came from
        return redirect(request.META.get("HTTP_REFERER", "courses:student_home"))

    user.full_name = full_name
    user.location = location
    user.bio = bio

    # Email: photo edit modal uses readonly—so don’t update it here
    # user.email = ...

    # Handle photo upload
    if "profile_photo" in request.FILES:
        user.profile_photo = request.FILES["profile_photo"]

    # Optional: handle remove photo flag if you use it in the modal
    if (request.POST.get("remove_photo") or "0") == "1":
        user.profile_photo = None

    user.save()
    messages.success(request, "Profile updated successfully!")

    if not next_url:
        return redirect("/")  # dashboard root

    return redirect(next_url)
