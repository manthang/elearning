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
# Course Detail
# =========================
@login_required
def course_detail_new(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    is_teacher = (user.role == user.Role.TEACHER)
    is_student = (user.role == user.Role.STUDENT)

    # same access pattern as course_detail
    can_view = True
    if is_teacher:
        can_view = Teaching.objects.filter(course=course, teacher=user).exists()
        dashboard_url = reverse("courses:teacher_home")
    elif is_student:
        dashboard_url = reverse("courses:student_home")
    else:
        dashboard_url = reverse("core:home") if "core:home" else "/"

    if not can_view:
        return HttpResponseForbidden("You don't have access to this course.")

    # -------------------------
    # GET: list all feedbacks
    # -------------------------
    if request.method == "GET":
        # base course detail context (so you can render the same course detail page)
        instructor = (
            Teaching.objects.filter(course=course)
            .select_related("teacher")
            .first()
        )
        instructor_user = instructor.teacher if instructor else None

        is_enrolled = False
        if is_student:
            is_enrolled = Enrollment.objects.filter(student=user, course=course).exists()

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

        feedbacks_qs = (
            CourseFeedback.objects
            .filter(course=course)
            .select_related("student")
            .order_by("-created_at")
        )

        total_feedbacks = feedbacks_qs.count()
        avg_rating = feedbacks_qs.aggregate(a=Avg("rating"))["a"] or 0
        avg_rating = round(float(avg_rating), 1) if total_feedbacks else 0

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
            "deadlines_count": deadlines.count(),
            "category_choices": Course.CATEGORY_CHOICES,
            "is_teacher_view": is_teacher and Teaching.objects.filter(course=course, teacher=user).exists(),
            "dashboard_url": dashboard_url,

            # feedback-specific
            "feedbacks": feedbacks_qs,
            "feedbacks_count": total_feedbacks,
            "avg_rating": avg_rating,
            "active_tab": "feedback",  # optional: if your template supports this
        }
        return render(request, "courses/course_detail/main.html", context)

    # -------------------------
    # POST: create/edit feedback (keep your existing logic)
    # -------------------------
    if user.role != user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    is_enrolled = Enrollment.objects.filter(student=user, course=course).exists()
    if not is_enrolled:
        return HttpResponseForbidden("You must be enrolled in this course to leave feedback.")

    existing = CourseFeedback.objects.filter(course=course, student=user).first()
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
    feedback.student = user
    feedback.save()

    messages.success(request, "Feedback submitted successfully!")
    return redirect(next_url)