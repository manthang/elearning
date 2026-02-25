import re
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Sum, Avg, Q, F
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..models import *
from ..forms import *

from apps.status.forms import *
from apps.status.models import *


# =========================
# Create Course
# =========================
@login_required
def course_create(request):

    if request.user.role != request.user.Role.TEACHER:
        return HttpResponseForbidden("Teachers only")

    COURSE_ID_RE = re.compile(r"^[A-Z0-9_-]+$")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        course_id_input = (request.POST.get("course_id") or "").strip().upper()

        category = (request.POST.get("category") or "").strip()
        duration = (request.POST.get("duration") or "").strip()

        # Validate max_students properly
        max_students_raw = (request.POST.get("max_students") or "").strip()
        max_students = None
        if max_students_raw:
            try:
                max_students = int(max_students_raw)
                if max_students <= 0:
                    messages.error(request, "Max students must be a positive number.")
                    return redirect("courses:teacher_home")
            except ValueError:
                messages.error(request, "Max students must be a number.")
                return redirect("courses:teacher_home")

        if not title:
            messages.error(request, "Course title is required.")
            return redirect("courses:teacher_home")

        # ✅ Validate category strictly
        valid_categories = {c[0] for c in Course.CATEGORY_CHOICES}
        if not category:
            category = Course.CATEGORY_GENERAL
        elif category not in valid_categories:
            messages.error(request, "Invalid category selected.")
            return redirect("courses:teacher_home")

        # Validate course_id ONLY if provided
        if course_id_input:
            if len(course_id_input) > 20:
                messages.error(request, "Course ID must be 20 characters or fewer.")
                return redirect("courses:teacher_home")

            if not COURSE_ID_RE.match(course_id_input):
                messages.error(request, "Course ID can only contain A–Z, 0–9, -, _")
                return redirect("courses:teacher_home")

            if Course.objects.filter(course_id=course_id_input).exists():
                messages.error(request, "Course ID already exists.")
                return redirect("courses:teacher_home")

        files = request.FILES.getlist("materials")

        with transaction.atomic():
            course = Course.objects.create(
                course_id=course_id_input or None,
                title=title,
                description=description,
                category=category,
                duration=duration,
                max_students=max_students,
            )

            Teaching.objects.create(
                teacher=request.user,
                course=course
            )

            for f in files:
                CourseMaterial.objects.create(
                    course=course,
                    file=f,
                    original_name=getattr(f, "name", "") or "",
                    uploaded_by=request.user
                )

        messages.success(request, "Course created successfully.")
        return redirect("courses:teacher_home")

    # If someone visits /course_create directly, still provide choices
    return render(request, "courses/course_create.html", {
        "category_choices": Course.CATEGORY_CHOICES
    })


# =========================
# Edit Course
# =========================
@login_required
@require_POST
def course_edit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    is_teacher = Teaching.objects.filter(course=course, teacher=request.user).exists()
    if not is_teacher:
        messages.error(request, "You don't have permission to edit this course.")
        return redirect("courses:course_detail", course_id=course.id)

    new_course_id = (request.POST.get("course_id") or "").strip()
    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()

    if not new_course_id:
        messages.error(request, "Course ID is required.")
        return redirect("courses:course_detail", course_id=course.id)

    if not title:
        messages.error(request, "Course title is required.")
        return redirect("courses:course_detail", course_id=course.id)

    # Core fields
    course.course_id = new_course_id
    course.title = title
    course.description = description

     # Category: validate against choices
    category = (request.POST.get("category") or "").strip()
    valid_categories = {k for k, _ in Course.CATEGORY_CHOICES}
    if category not in valid_categories:
        messages.error(request, "Invalid category selected.")
        return redirect("courses:course_detail", course_id=course.id)
    course.category = category

    # Duration
    course.duration = (request.POST.get("duration") or "").strip() or None

    # Max students
    max_students_raw = (request.POST.get("max_students") or "").strip()
    course.max_students = int(max_students_raw) if max_students_raw.isdigit() else None

    try:
        course.save()
        messages.success(request, "Course updated.")
    except IntegrityError:
        messages.error(request, "That Course ID is already used. Please choose another one.")

    return redirect("courses:course_detail", course_id=course.id)


# =========================
# Course Detail
# =========================
@login_required
def course_detail(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    is_teacher = (user.role == user.Role.TEACHER)
    is_student = (user.role == user.Role.STUDENT)

    can_view = True
    if is_teacher:
        can_view = Teaching.objects.filter(course=course, teacher=user).exists()
        dashboard_url = reverse("courses:teacher_home")
    elif is_student:
        dashboard_url = reverse("courses:student_home")

    if not can_view:
        return HttpResponseForbidden("You don't have access to this course.")

    # Instructor (first teacher linked)
    instructor = (
        Teaching.objects.filter(course=course)
        .select_related("teacher")
        .first()
    )
    instructor_user = instructor.teacher if instructor else None

    is_enrolled = False
    if request.user.is_authenticated and request.user.role == request.user.Role.STUDENT:
        is_enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()

    enrollments = (
        Enrollment.objects
        .filter(course=course)
        .select_related("student")
        .order_by("-id")
    )

    enrollment_count = enrollments.count()
    avg_progress = enrollments.aggregate(a=Avg("progress"))["a"] or 0
    avg_progress = int(round(avg_progress))

    materials = (
        CourseMaterial.objects
        .filter(course=course)
        .order_by("-uploaded_at")
    )

    deadlines = (
        Deadline.objects
        .filter(course=course)
        .order_by("due_at")
    )

    context = {
        "course": course,
        "is_enrolled": is_enrolled,
        "instructor_user": instructor_user,
        "enrollments": enrollments,
        "enrollment_count": enrollment_count,
        "avg_progress": avg_progress,
        "materials": materials,
        "materials_count": materials.count(),
        "deadlines": deadlines,
        "category_choices": Course.CATEGORY_CHOICES,
        "is_teacher_view": is_teacher and Teaching.objects.filter(course=course, teacher=user).exists(),
        "dashboard_url": dashboard_url,
    }
    return render(request, "courses/course_detail/main.html", context)


# =========================
# Enroll Course
# =========================
@login_required
def course_enroll(request, course_id):
    if request.user.role != request.user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    # enforce max_students if set
    if course.max_students is not None:
        current = Enrollment.objects.filter(course=course).count()
        if current >= course.max_students:
            messages.error(request, "This course is full.")
            return redirect("courses:student_home")


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


# =========================
# Course Feedback
# =========================
@login_required
@require_POST
def course_feedback(request, course_id):
    if request.user.role != request.user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    is_enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
    if not is_enrolled:
        return HttpResponseForbidden("You must be enrolled in this course to leave feedback.")

    existing = CourseFeedback.objects.filter(course=course, student=request.user).first()
    form = CourseFeedbackForm(request.POST, instance=existing)

    # safe "next" redirect (fallback to student_home)
    next_url = request.POST.get("next")
    if not next_url or not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = redirect("courses:student_home").url

    if not form.is_valid():
        messages.error(request, "Please provide a valid rating (1–5).")
        return redirect(next_url)

    feedback = form.save(commit=False)
    feedback.course = course
    feedback.student = request.user
    feedback.save()

    messages.success(request, "Feedback submitted successfully!")
    return redirect(next_url)
