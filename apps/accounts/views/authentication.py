from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages

from ..models import *

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
