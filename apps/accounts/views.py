from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import *
from apps.courses.models import *

User = get_user_model()

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        full_name = request.POST.get("fullname", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        role = request.POST.get("role", "STUDENT")

        # ✅ whitelist roles
        if role not in [User.Role.STUDENT, User.Role.TEACHER]:
            role = User.Role.STUDENT

        # ❌ basic duplicate check
        if User.objects.filter(username=username).exists():
            return render(request, "accounts/signup.html", {
                "error": "Username already exists"
            })

        user = User.objects.create_user(
            username=username,
            full_name=full_name,
            email=email,
            password=password,
            role=role,
        )

        login(request, user)
        return redirect("core:home")

    return render(request, "accounts/signup.html")


def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST["username"],
            password=request.POST["password"],
        )
        if user:
            login(request, user)
            return redirect("core:home")
        messages.error(request, "Invalid credentials")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def user_search(request):
    query = request.GET.get("q", "")
    role = request.GET.get("role", "student")

    users = User.objects.filter(
        role=role.upper()
    ).filter(
        Q(full_name__icontains=query) |
        Q(email__icontains=query)
    )[:10]

    results = []
    for u in users:
        results.append({
            "id": u.id,
            "name": u.full_name or u.username,
            "email": u.email,
            "location": u.location or "",
            "avatar": u.profile_photo.url if u.profile_photo else "media/profile_photos/default-avatar.svg",
        })

    return JsonResponse({"results": results})


@login_required
def user_profile(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise Http404

    enrolled_count = Enrollment.objects.filter(student=user).count()

    data = {
        "id": user.id,
        "full_name": user.full_name or user.username,
        "role": user.get_role_display(),
        "email": user.email,
        "location": user.location,
        "bio": user.bio,
        "joined": user.date_joined.strftime("%b %Y"),
        "avatar": user.avatar_url if hasattr(user, "avatar_url") else None,
        "enrolled_courses": enrolled_count
    }

    return JsonResponse(data)
