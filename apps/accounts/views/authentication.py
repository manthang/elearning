from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages

from ..models import *

User = get_user_model()


def signup_view(request):
    # Only process the data if the user has submitted the form
    if request.method == "POST":
        
        # Extract and sanitize form data (strip removes accidental leading/trailing spaces)
        username = request.POST.get("username", "").strip()
        full_name = request.POST.get("fullname", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        role = request.POST.get("role", "STUDENT")

        # Whitelist roles
        # Security measure: Prevents malicious users from inspecting the HTML 
        # and submitting a custom role (like "ADMIN" or "STAFF")
        if role not in [User.Role.STUDENT, User.Role.TEACHER]:
            role = User.Role.STUDENT

        # Username duplicate check
        # Queries the database to ensure no two users share the same username
        if User.objects.filter(username=username).exists():
            return render(request, "accounts/signup.html", {
                "error": "That username is already taken. Please choose another."
            })

        # Email duplicate check
        # Queries the database to ensure the email isn't already attached to an account
        if User.objects.filter(email=email).exists():
            return render(request, "accounts/signup.html", {
                "error": "An account with that email address already exists."
            })

        # Create the user
        # create_user is a built-in Django method that securely hashes the 
        # password before saving the record to the database
        user = User.objects.create_user(
            username=username,
            full_name=full_name,
            email=email,
            password=password,
            role=role,
        )

        # Automatically establish a session for the user so they don't 
        # have to log in immediately after signing up
        login(request, user)
        
        # Send the newly authenticated user to the main dashboard
        return redirect("core:home")

    # If the request is a GET (the user just clicked a link to arrive here),
    # simply render the empty form template.
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
