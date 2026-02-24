from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

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


@login_required
def user_profile(request, username):
    u = get_object_or_404(User, username=username)

    # Safe field reads
    full_name = getattr(u, "full_name", "") or u.get_full_name() or u.username
    location = getattr(u, "location", "") or ""
    bio = getattr(u, "bio", "") or ""

    # Role display (safe)
    if hasattr(u, "get_role_display"):
        role_display = u.get_role_display()
    else:
        role_display = str(getattr(u, "role", "") or "")

    # Avatar (safe + correct MEDIA_URL)
    profile_photo = getattr(u, "profile_photo", None)
    avatar_url = profile_photo.url if profile_photo else f"{settings.MEDIA_URL}profile_photos/default-avatar.svg"

    # Enrolled courses (safe)
    enrolled_count = Enrollment.objects.filter(student_id=u.id).count()

    data = {
        "id": u.id,
        "full_name": full_name,
        "role": role_display,
        "email": u.email,
        "location": location,
        "bio": bio,
        "joined": u.date_joined.strftime("%b %Y"),
        "avatar": avatar_url,
        "enrolled_courses": enrolled_count,
    }
    return JsonResponse(data)


@login_required
@require_POST
def edit_profile(request):
    user = request.user

    next_url = (request.POST.get("next") or "").strip()

    full_name = (request.POST.get("full_name") or "").strip()
    location = (request.POST.get("location") or "").strip()
    bio = (request.POST.get("bio") or "").strip()

    if not full_name:
        messages.error(request, "Full name is required.")
        fallback = request.META.get("HTTP_REFERER")
        # only redirect to referrer if it’s same host
        if fallback and url_has_allowed_host_and_scheme(
            url=fallback,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(fallback)
        return redirect(reverse("courses:student_home"))

    user.full_name = full_name
    user.location = location
    user.bio = bio

    # Handle photo upload (optional basic validation)
    photo = request.FILES.get("profile_photo")
    if photo:
        if not (photo.content_type or "").startswith("image/"):
            messages.error(request, "Please upload an image file.")
            return redirect(reverse("courses:student_home"))  # or safe referrer as above
        user.profile_photo = photo

    # Remove photo flag
    if (request.POST.get("remove_photo") or "0") == "1":
        user.profile_photo = None

    user.save()
    messages.success(request, "Profile updated successfully!")

    # Safe redirect for next_url
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect("/")  # or reverse("courses:student_home") / role-based dashboard
