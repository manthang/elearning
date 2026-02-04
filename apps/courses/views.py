from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.utils.timezone import now

from .models import *
from .forms import *

from apps.core.models import StatusUpdate
from apps.core.forms import StatusUpdateForm

from django.contrib import messages

@login_required
def teacher_home(request):
    user = request.user
    if user.role != user.Role.TEACHER:
        return HttpResponseForbidden("Teachers only")

    # courses = Course.objects.filter(
    #     sections__teaching__teacher=user
    # ).distinct()

    return render(request, "courses/teacher_home.html")

@login_required
def student_home(request):
    user = request.user

    # 🔒 Students only
    if user.role != user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    tab = request.GET.get("tab", "courses")

    # ================= PROFILE UPDATE =================
    if request.method == "POST" and "full_name" in request.POST:
        user.full_name = request.POST.get("full_name", "").strip()
        user.email = request.POST.get("email", "").strip()
        user.location = request.POST.get("location", "").strip()
        user.bio = request.POST.get("bio", "").strip()

        if "profile_photo" in request.FILES:
            user.profile_photo = request.FILES["profile_photo"]

        user.save()
        messages.success(request, "Profile updated successfully!")
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

    # ================= ENROLLMENTS =================
    enrollments = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course")
    )

    enrolled_course_ids = set()
    enrolled_courses = []

    for enrollment in enrollments:
        course = enrollment.course
        enrolled_course_ids.add(course.id)

        # derived fields (NOT model fields)
        course.is_enrolled = True
        course.progress = enrollment.progress

        # attach teachers
        course.teachers = [
            t.teacher
            for t in Teaching.objects.filter(course=course)
                                     .select_related("teacher")
        ]

        # attach existing feedback (if any)
        feedback = CourseFeedback.objects.filter(
            course=course,
            student=user
        ).first()

        course.feedback_rating = feedback.rating if feedback else 0
        course.feedback_comment = feedback.comment if feedback else ""

        enrolled_courses.append(course)

    # ================= ALL COURSES =================
    all_courses = Course.objects.all()

    for course in all_courses:
        course.is_enrolled = course.id in enrolled_course_ids
        course.progress = 0

        # attach teachers
        course.teachers = [
            t.teacher
            for t in Teaching.objects.filter(course=course)
                                     .select_related("teacher")
        ]

        # attach feedback only if enrolled
        if course.is_enrolled:
            feedback = CourseFeedback.objects.filter(
                course=course,
                student=user
            ).first()
            course.feedback_rating = feedback.rating if feedback else 0
            course.feedback_comment = feedback.comment if feedback else ""
        else:
            course.feedback_rating = 0
            course.feedback_comment = ""

    enrolled_count = len(enrolled_courses)

    # ================= DEADLINES & UPDATES =================
    show_past = request.GET.get("show_past") == "1"
    
    deadlines = Deadline.objects.filter(
        course_id__in=enrolled_course_ids,
    )
    if not show_past:
        deadlines = deadlines.filter(due_at__gte=timezone.now())

    deadlines = deadlines.order_by("due_at")[:5]

    updates = StatusUpdate.objects.select_related("author")[:20]

    context = {
        "tab": tab,
        "courses": enrolled_courses,      # My Courses
        "all_courses": all_courses,        # All Courses
        "enrolled_count": enrolled_count,
        "deadlines": deadlines,
        "show_past": show_past,
        "updates": updates,
        "form": form,
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
def course_enroll(request, course_id):
    if request.user.role != request.user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    # 🔒 Course must have at least one teacher
    if not Teaching.objects.filter(course=course).exists():
        return HttpResponseForbidden(
            "This course is not yet available for enrollment."
        )

    Enrollment.objects.get_or_create(
        student=request.user,
        course=course
    )

    return redirect("courses:student_home")


@login_required
def course_feedback(request, course_id):
    if request.user.role != request.user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    # 🔒 ENFORCE enrollment
    is_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course
    ).exists()

    if not is_enrolled:
        return HttpResponseForbidden(
            "You must be enrolled in this course to leave feedback."
        )

    form = CourseFeedbackForm(request.POST)

    if not form.is_valid():
        # NEVER save anything if form is invalid
        return redirect("courses:student_home")

    CourseFeedback.objects.update_or_create(
        course=course,
        student=request.user,
        defaults={
            "rating": form.cleaned_data["rating"],
            "comment": form.cleaned_data.get("comment", ""),
        }
    )

    messages.success(request, "Feedback submitted successfully!")
    return redirect("courses:student_home")


@login_required
def course_continue(request, course_id):
    if request.user.role != request.user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    return render(request, "courses/course_detail.html", {
        "course": course
    })
