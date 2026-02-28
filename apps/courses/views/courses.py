import re
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError
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

    # Determine where to send the user after processing
    # Fallback to the course detail page if no 'next' parameter is provided
    fallback_url = redirect("courses:course_detail", course_id=course.id)
    next_url = request.POST.get("next")
    redirect_target = redirect(next_url) if next_url else fallback_url

    # Permission Check
    is_teacher = Teaching.objects.filter(course=course, teacher=request.user).exists()
    if not is_teacher:
        messages.error(request, "You don't have permission to edit this course.")
        return redirect_target

    # Extract core fields (Notice we ignore course_id as it shouldn't change)
    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()
    category = (request.POST.get("category") or "").strip()

    # Validation
    if not title:
        messages.error(request, "Course title is required.")
        return redirect_target

    valid_categories = {k for k, _ in Course.CATEGORY_CHOICES}
    if category not in valid_categories:
        messages.error(request, "Invalid category selected.")
        return redirect_target

    # Apply Updates
    course.title = title
    course.description = description
    course.category = category
    course.duration = (request.POST.get("duration") or "").strip() or None

    max_students_raw = (request.POST.get("max_students") or "").strip()
    course.max_students = int(max_students_raw) if max_students_raw.isdigit() else None

    #Save
    try:
        course.save()
        messages.success(request, "Course updated successfully.")
    except Exception as e:
        messages.error(request, f"An error occurred while saving: {str(e)}")

    return redirect_target


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

    return redirect(f"{reverse('courses:course_detail', args=[course.id])}?tab=overview")


# =========================
# Course Feedback
# =========================
def course_feedback(request, course_id):
    # Security Check
    if not request.user.is_student:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    # Enrollment Check
    is_enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
    if not is_enrolled:
        return HttpResponseForbidden("You must be enrolled to leave feedback.")

    # Redirect back to the originating page (dashboard or detail view) after saving
    # Priority: 1. 'next' hidden input, 2. Referer header, 3. Default dashboard
    next_url = request.POST.get("next") or request.META.get('HTTP_REFERER')
    
    # Security: Ensure the URL is safe and internal
    if not next_url or not url_has_allowed_host_and_scheme(
        url=next_url, 
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        next_url = reverse("courses:student_home")

    # Handle Form
    existing = CourseFeedback.objects.filter(course=course, student=request.user).first()
    form = CourseFeedbackForm(request.POST, instance=existing)

    if not form.is_valid():
        # Capture specific errors if necessary
        error_msg = form.errors.as_text() if form.errors else "Please provide a valid rating (1–5)."
        messages.error(request, error_msg)
        return redirect(next_url)

    # Save Data
    feedback = form.save(commit=False)
    feedback.course = course
    feedback.student = request.user
    feedback.save()

    messages.success(request, "Feedback submitted successfully!")
    return redirect(next_url)
