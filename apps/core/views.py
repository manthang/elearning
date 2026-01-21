from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import StatusUpdate
from .forms import StatusUpdateForm

@login_required
def status_feed(request):
    updates = StatusUpdate.objects.select_related("author")[:20]

    form = None
    if request.user.role == "student":
        if request.method == "POST":
            form = StatusUpdateForm(request.POST)
            if form.is_valid():
                status = form.save(commit=False)
                status.author = request.user
                status.save()
                return redirect("core:status_feed")
        else:
            form = StatusUpdateForm()

    return render(
        request,
        "core/status_feed.html",
        {
            "updates": updates,
            "form": form,
        },
    )


def home_redirect(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if request.user.role == "teacher":
        return redirect("courses:teacher_home")

    return redirect("courses:student_home")

