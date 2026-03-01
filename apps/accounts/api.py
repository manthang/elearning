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
    
    # Default to an empty string instead of "STUDENT"
    role = request.GET.get("role", "").upper()

    # Start with all active users
    users = User.objects.filter(is_active=True)

    # Only filter by role if the frontend specifically asked for one
    if role and role != "ALL":
        users = users.filter(role=role)

    # Apply the text search
    if query:
        users = users.filter(
            Q(full_name__icontains=query) | 
            Q(username__icontains=query) | 
            Q(email__icontains=query)
        )

    # Limit results to 15 to keep the chat search UI snappy
    results = [get_user_data_payload(u) for u in users[:15]]
    
    return JsonResponse({"results": results})
