from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..models import *
from ..forms import SignupForm

User = get_user_model()


def signup_view(request):
    # Prevent logged-in users from accessing the signup page
    if request.user.is_authenticated:
        return redirect("core:home")

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
    # Prevent already logged-in users from seeing the login page
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        # Safely extract data using .get() to prevent KeyErrors
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            
            # Handle the "next" parameter for seamless UX
            next_url = request.GET.get("next")
            
            # Security check: Ensure the next_url is safe and on your domain 
            # (prevents Open Redirect vulnerabilities)
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)
            else:
                return redirect("core:home")
                
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


# Add the @require_POST decorator to ensure no one can accidentally (or maliciously)
# trigger a logout just by visiting the URL.
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect("accounts:login")
