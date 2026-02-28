from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch, Avg, Count
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render, get_object_or_404

from apps.courses.models import *

User = get_user_model()


# ==========================================
# HELPER FUNCTIONS (Data Access Layer)
# ==========================================
def _get_enrolled_courses_data(user):
    """Fetches courses a specific user is enrolled in, with teachers and progress."""
    enrollments = Enrollment.objects.filter(student=user)
    progress_map = {e.course_id: e.progress for e in enrollments}
    enrolled_course_ids = set(progress_map.keys())

    teachers_prefetch = Prefetch(
        "teachings",
        queryset=Teaching.objects.select_related("teacher"),
        to_attr="course_teachings"
    )
    
    user_feedback_prefetch = Prefetch(
        "feedbacks",
        queryset=CourseFeedback.objects.filter(student=user),
        to_attr="user_feedbacks"
    )

    # Fetch only the courses this user is enrolled in
    courses_qs = Course.objects.filter(id__in=enrolled_course_ids).prefetch_related(
        teachers_prefetch, user_feedback_prefetch
    )

    enrolled_courses = []
    for course in courses_qs:
        course.progress = progress_map.get(course.id, 0)
        course.teachers = [t.teacher for t in course.course_teachings]
        
        feedback = course.user_feedbacks[0] if course.user_feedbacks else None
        course.feedback_rating = feedback.rating if feedback else 0
        course.feedback_comment = feedback.comment if feedback else ""
        
        enrolled_courses.append(course)

    return enrolled_courses, enrolled_course_ids

def _get_all_courses_catalog(enrolled_course_ids):
    """Fetches the global course catalog with average ratings."""
    teachers_prefetch = Prefetch("teachings", queryset=Teaching.objects.select_related("teacher"), to_attr="course_teachings")
    
    catalog_qs = Course.objects.annotate(
        avg_rating=Avg("feedbacks__rating"),
        rating_count=Count("feedbacks")
    ).prefetch_related(teachers_prefetch)

    all_courses = []
    for course in catalog_qs:
        course.is_enrolled = course.id in enrolled_course_ids
        course.teachers = [t.teacher for t in course.course_teachings]
        all_courses.append(course)
        
    return all_courses

@login_required
def dashboard_redirect(request):
    """Simply redirects /home/ to the user's personal @username URL."""
    return redirect("accounts:user_profile", username=request.user.username)


@login_required
def user_profile(request, username):
    """Unified view for both Private Dashboard and Public Profile."""
    profile_user = get_object_or_404(User, username=username)
    is_own_profile = (request.user == profile_user)
    
    tab = request.GET.get("tab", "courses")
    show_past = request.GET.get("show_past") == "1"

    # 1. Fetch the user's enrolled courses
    enrolled_courses, enrolled_course_ids = _get_enrolled_courses_data(profile_user)

    # 2. Conditional Fetching (Huge Performance Boost)
    # We ONLY fetch the entire course catalog if the user is looking at their OWN dashboard
    # and they specifically clicked the "All Courses" tab. 
    all_courses = []
    if is_own_profile and tab == "all":
        all_courses = _get_all_courses_catalog(enrolled_course_ids)

    # 3. Fetch Deadlines
    deadlines = Deadline.objects.filter(course_id__in=enrolled_course_ids)
    if not show_past:
        deadlines = deadlines.filter(due_at__gte=timezone.now())
    deadlines = deadlines.order_by("due_at")[:5]

    # 4. Fetch Status Updates
    status_updates = profile_user.status_updates.select_related("author").prefetch_related("liked_by")[:20]

    context = {
        "profile_user": profile_user,
        "is_own_profile": is_own_profile,
        "tab": tab,
        
        # Data
        "enrolled_courses": enrolled_courses,
        "all_courses": all_courses,
        "deadlines": deadlines,
        "statuses": status_updates,
        "show_past": show_past,
        "enrolled_count": len(enrolled_courses),
    }

    return render(request, "accounts/profile.html", context)


@login_required
@require_POST
def edit_profile(request):
    """Dedicated endpoint to handle profile form submissions."""
    user = request.user
    user.full_name = request.POST.get("full_name", "").strip()
    user.location = request.POST.get("location", "").strip()
    user.bio = request.POST.get("bio", "").strip()
    
    if "profile_photo" in request.FILES:
        user.profile_photo = request.FILES["profile_photo"]
        
    user.save()
    messages.success(request, "Profile updated successfully!")
    
    # Safely redirect back to where they were
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if not next_url:
        next_url = reverse("accounts:user_profile", args=[user.username])
        
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
        avatar_url = (
            u.profile_photo.url
            if u.profile_photo
            else f"{settings.MEDIA_URL}profile_photos/default-avatar.svg"
        )

        results.append({
            "id": u.id,
            "username": u.username,
            "name": u.full_name or u.username,
            "email": u.email,
            "location": u.location or "",
            "avatar": avatar_url,
        })

    return JsonResponse({"results": results})
