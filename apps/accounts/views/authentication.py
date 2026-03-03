from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import render, redirect

from ..models import *
from ..forms import SignupForm

User = get_user_model()


def signup_view(request):
    if request.method == "POST":
        # Pass the incoming POST data directly into the form
        form = SignupForm(request.POST)
        
        # This triggers all your clean_email, clean_username, and empty string checks
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("core:home")
            
        # If is_valid() is False, it skips the redirect and falls through to the render below,
        # carrying all the error messages inside the `form` object.
    else:
        form = SignupForm()

    # Pass the form object to the template
    return render(request, "accounts/signup.html", {"form": form})


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
