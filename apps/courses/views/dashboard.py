
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
# Teacher Home Page
# =========================
@login_required
def teacher_home(request):
    user = request.user
    if user.role != user.Role.TEACHER:
        return HttpResponseForbidden("Teachers only")

    # Courses taught by this teacher
    my_courses = (
        Course.objects
        .filter(teachings__teacher=user)
        .annotate(
            students_total=Count("enrollments", distinct=True),
            materials_total=Count("materials", distinct=True),
        )
        .order_by("-updated_at", "-created_at", "title")
        .distinct()
    )

    # Stats
    courses_created = my_courses.count()
    active_courses = courses_created  # we don't have an "archived" flag yet

    # total enrolled across teacher courses (sum of enrollments)
    total_enrolled = (
        Enrollment.objects
        .filter(course__teachings__teacher=user)
        .count()
    )

    # total unique students across teacher courses
    total_students = (
        Enrollment.objects
        .filter(course__teachings__teacher=user)
        .values("student_id")
        .distinct()
        .count()
    )

    total_materials = (
        CourseMaterial.objects
        .filter(course__teachings__teacher=user)
        .count()
    )

    # Capacity used % across capped courses only
    capped_qs = my_courses.filter(max_students__isnull=False)
    capacity_total = capped_qs.aggregate(total=Sum("max_students"))["total"] or 0

    capped_enrolled = (
        Enrollment.objects
        .filter(course__teachings__teacher=user, course__max_students__isnull=False)
        .count()
    )

    capacity_used_pct = None
    if capacity_total > 0:
        capacity_used_pct = round((capped_enrolled / capacity_total) * 100)

    # Teacher deadlines (reuse existing upcoming_deadlines component)
    show_past = request.GET.get("show_past") == "1"
    deadlines = Deadline.objects.filter(course__teachings__teacher=user)
    if not show_past:
        deadlines = deadlines.filter(due_at__gte=timezone.now())
    deadlines = deadlines.order_by("due_at")[:5]

    context = {
        "my_courses": my_courses,
        
        # for Create / Edit Course modal dropdown
        "category_choices": Course.CATEGORY_CHOICES,

        # stats used by teacher_overview_strip.html
        "courses_created": courses_created,
        "active_courses": active_courses,
        "total_students": total_students,
        "total_materials": total_materials,
        "total_enrolled": total_enrolled,
        "capacity_used_pct": capacity_used_pct,

        # for upcoming_deadlines.html
        "deadlines": deadlines,
        "show_past": show_past,
    }
    return render(request, "courses/teacher_home.html", context)


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
    status_form = StatusUpdateForm()
    status_updates = StatusUpdate.objects.select_related("author")[:20]

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

    context = {
        "tab": tab,
        "courses": enrolled_courses,      # My Courses
        "all_courses": all_courses,        # All Courses
        "enrolled_courses": enrolled_courses, # add (template-friendly)
        "enrolled_course_ids": enrolled_course_ids,  # add (for badges/logic)
        "enrolled_count": enrolled_count,
        "deadlines": deadlines,
        "show_past": show_past,
        "updates": status_updates,
        "form": status_form,
    }

    return render(request, "courses/student_home.html", context)
