from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.formats import date_format
from django.db.models import Q

User = get_user_model()

def get_user_data_payload(user):
    """Unified data structure for search results and profile view."""
    data = {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "role": user.get_role_display(),
        "email": user.email,
        "location": user.location or "—",
        "joined": user.date_joined.strftime("%B %Y"),
        "bio": user.bio or "No bio available.",
        "avatar_url": user.avatar_url,
    }

    if user.is_teacher:
        # Access through the 'teachings' related_name on the Teaching model
        data["teaching_courses"] = [
            {"id": t.course.id, "title": t.course.title} 
            for t in user.teachings.all().select_related('course')
        ]
        data["enrolled_courses"] = None
    else:
        # For students, count via 'enrollments' related_name
        data["enrolled_courses"] = user.enrollments.count()
        data["teaching_courses"] = None
        
    return data


# =========================
# User Profile API
# =========================
@login_required
def user_profile_api(request, username):
    profile_user = get_object_or_404(User, username=username)
    return JsonResponse(get_user_data_payload(profile_user))


# =========================
# User Search
# =========================
@login_required
def user_search(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "STUDENT").upper() # Normalize to match TextChoices

    # Don't hit the DB if the query is empty
    if not query:
        return JsonResponse({"results": []})

    users = User.objects.filter(role=role)

    users = users.filter(
        Q(full_name__icontains=query) |
        Q(email__icontains=query) |
        Q(username__icontains=query)
    )[:10]

    results = [get_user_data_payload(u) for u in users]

    return JsonResponse({"results": results})
