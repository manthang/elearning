from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from .forms import *


@login_required
def post_status(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("courses:student_home"))

    form = StatusUpdateForm(request.POST)
    if form.is_valid():
        status = form.save(commit=False)
        status.author = request.user
        status.save()

    return HttpResponseRedirect(
        reverse("courses:student_home") + "?tab=status"
    )
