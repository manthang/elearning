from django.shortcuts import redirect

def home_redirect(request):
    # Not logged in? Go to login or a public landing page.
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    # Logged in? Send them to the accounts home redirect, 
    # which will safely bounce them to /@theirusername/
    return redirect("accounts:home")
