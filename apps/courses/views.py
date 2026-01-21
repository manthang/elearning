from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.utils.timezone import now

from .models import Course, CourseFeedback, Enrollment

from apps.core.models import StatusUpdate
from apps.core.forms import StatusUpdateForm
from apps.core.models import Deadline

@login_required
def teacher_home(request):
    if request.user.role != "teacher":
        return HttpResponseForbidden("Teachers only")

    courses = Course.objects.filter(teacher=request.user)
    return render(request, "courses/teacher_home.html", {"courses": courses})

@login_required
def student_home(request):
    user = request.user

    if user.role != "student":
        return HttpResponseForbidden("Students only")

    enrolled_count = Enrollment.objects.filter(student=user).count()

    # default tab
    tab = request.GET.get("tab", "courses")

    deadlines = Deadline.objects.filter(
        due_at__gte=now()
    ).order_by("due_at")[:5]

    updates = StatusUpdate.objects.select_related("author")[:20]

    # ================= PROFILE UPDATE =================
    if request.method == "POST" and "full_name" in request.POST:
        user.full_name = request.POST.get("full_name", "").strip()
        user.email = request.POST.get("email", "").strip()
        user.location = request.POST.get("location", "").strip()
        user.bio = request.POST.get("bio", "").strip()

        if "profile_photo" in request.FILES:
            user.profile_photo = request.FILES["profile_photo"]

        user.save()
        return redirect("courses:student_home")

    # ================= STATUS UPDATE =================
    form = StatusUpdateForm()

    if request.method == "POST" and tab == "status":
        form = StatusUpdateForm(request.POST)
        if form.is_valid():
            status = form.save(commit=False)
            status.author = user
            status.save()
            return redirect("courses:student_home") + "?tab=status"

    context = {
        "tab": tab,
        "enrolled_count": enrolled_count,
        "updates": updates,
        "form": form,
        "deadlines": deadlines,
    }

    return render(request, "courses/student_home.html", context)

@login_required
def course_create(request):
    if request.user.role != "teacher":
        return HttpResponseForbidden("Teachers only")

    if request.method == "POST":
        Course.objects.create(
            title=request.POST["title"],
            description=request.POST.get("description", ""),
            teacher=request.user,
        )
        return redirect("courses:teacher_home")

    return render(request, "courses/course_create.html")


@login_required
def enrol_course(request, course_id):
    if request.user.role != "student":
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)
    course.students.add(request.user)
    return redirect("courses:student_home")


@login_required
def leave_feedback(request, course_id):
    if request.user.role != "student":
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        CourseFeedback.objects.create(
            course=course,
            student=request.user,
            comment=request.POST["comment"],
            rating=request.POST.get("rating", 5),
        )
        return redirect("courses:student_home")

    return render(request, "courses/feedback.html", {"course": course})
