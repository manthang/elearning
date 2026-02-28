from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch, Avg, Count
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse

from apps.courses.models import *
from apps.courses.utils import _get_enrolled_courses_data, _get_all_courses_catalog
from ..utils import _get_teacher_profile_data


User = get_user_model()


@login_required
def dashboard_redirect(request):
    """Simply redirects /home/ to the user's personal @username URL."""
    return redirect("accounts:user_profile", username=request.user.username)


@login_required
def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    is_own_profile = (request.user == profile_user)
    
    tab = request.GET.get("tab", "courses")
    show_past = request.GET.get("show_past") == "1"

    context = {
        "profile_user": profile_user,
        "is_own_profile": is_own_profile,
        "tab": tab,
        "show_past": show_past,
    }

    # ================= ROLE-BASED ROUTING =================
    if profile_user.role == profile_user.Role.TEACHER:
        # Teacher Logic
        taught_courses, teacher_stats = _get_teacher_profile_data(profile_user, is_own_profile)
        
        # Deadlines
        deadlines = Deadline.objects.filter(course__teachings__teacher=profile_user)
        if not show_past:
            deadlines = deadlines.filter(due_at__gte=timezone.now())
        
        context.update(teacher_stats)  # Unpacks stats dict directly into context
        context["taught_courses"] = taught_courses
        context["deadlines"] = deadlines.order_by("due_at")[:5]

    else:
        # Student Logic (The helper we wrote previously)
        enrolled_courses, enrolled_course_ids = _get_enrolled_courses_data(profile_user)
        
        # Public "All Courses" tab catalog
        all_courses = []
        if is_own_profile and tab == "all":
            all_courses = _get_all_courses_catalog(enrolled_course_ids)
            
        # Deadlines
        deadlines = Deadline.objects.filter(course_id__in=enrolled_course_ids)
        if not show_past:
            deadlines = deadlines.filter(due_at__gte=timezone.now())

        context["enrolled_courses"] = enrolled_courses
        context["all_courses"] = all_courses
        context["enrolled_count"] = len(enrolled_courses)
        context["deadlines"] = deadlines.order_by("due_at")[:5]

    # ================= SHARED LOGIC =================
    # Both students and teachers have the social wall!
    if tab == "status":
        context["statuses"] = profile_user.status_updates.select_related("author").prefetch_related("liked_by")[:20]

    return render(request, "accounts/profile.html", context)


@login_required
@require_POST
def edit_profile(request):
    user = request.user
    
    # Update text fields
    user.full_name = request.POST.get("full_name", "").strip()
    user.location = request.POST.get("location", "").strip()
    user.bio = request.POST.get("bio", "").strip()

    # Handle explicitly removing the photo
    if request.POST.get("remove_photo") == "1":
        if user.profile_photo:
            # Delete the actual image file from your media folder to save space
            user.profile_photo.delete(save=False) 
        # Clear the database field
        user.profile_photo = None 

    # Handle uploading a new photo
    elif "profile_photo" in request.FILES:
        if user.profile_photo:
            user.profile_photo.delete(save=False) # Clean up the old one first
        user.profile_photo = request.FILES["profile_photo"]

    user.save()
    messages.success(request, "Profile updated successfully!")

    # Safely redirect back to wherever they were
    next_url = request.POST.get("next") or reverse("accounts:user_profile", kwargs={"username": user.username})
    return redirect(next_url)


@login_required
def user_search(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role")

    users = User.objects.all()

    # Filter by role if provided
    if role:
        users = users.filter(role__iexact=role)

    # Filter by search query
    if query:
        users = users.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query)
        )

    users = users[:10]

    results = []
    for u in users:
        results.append({
            "id": u.id,
            "username": u.username,
            "name": u.full_name or u.username,
            "email": u.email,
            "location": u.location or "",
            "avatar": u.avatar_url,
        })

    return JsonResponse({"results": results})
