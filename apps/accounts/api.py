from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.formats import date_format
from django.db.models import Q

User = get_user_model()

def get_user_data_payload(user):
    """Helper function to ensure consistent data across all User APIs."""
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "role": user.get_role_display(),
        "email": user.email,
        "location": user.location or "—",
        "joined": user.date_joined.strftime("%B %Y"),
        "bio": user.bio or "No bio available.",
        "avatar_url": user.avatar_url, #
        "enrolled_courses": user.enrollments.count() if user.is_student else None
    }


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
    role = request.GET.get("role", "").upper() # Normalize to match TextChoices

    # Don't hit the DB if the query is empty
    if not query:
        return JsonResponse({"results": []})

    users = User.objects.all()

    if role:
        users = users.filter(role=role) # Exact match is faster than iexact

    users = users.filter(
        Q(full_name__icontains=query) |
        Q(email__icontains=query) |
        Q(username__icontains=query) # Added username search for better UX
    )[:10]

    results = [get_user_data_payload(u) for u in users]

    return JsonResponse({"results": results})
