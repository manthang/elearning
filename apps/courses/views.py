
import re

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Sum, Avg, Q, F
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone


from .models import *
from .forms import *

from apps.status.forms import *
from apps.status.models import *


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
    active_courses = courses_created  # you don't have an "archived" flag yet

    # total enrolled across teacher courses (sum of enrollments)
    total_enrolled = (
        Enrollment.objects
        .filter(course__teachings__teacher=user)
        .count()
    )

    # total unique students across teacher courses (optional but useful)
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
def course_create(request):

    if request.user.role != request.user.Role.TEACHER:
        return HttpResponseForbidden("Teachers only")

    COURSE_ID_RE = re.compile(r"^[A-Z0-9_-]+$")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        course_id_input = (request.POST.get("course_id") or "").strip().upper()

        category = (request.POST.get("category") or Course.CATEGORY_GENERAL).strip()
        duration = (request.POST.get("duration") or "").strip()

        max_students_raw = (request.POST.get("max_students") or "").strip()
        max_students = None
        if max_students_raw:
            try:
                max_students = int(max_students_raw)
                if max_students <= 0:
                    max_students = None
            except ValueError:
                max_students = None

        if not title:
            messages.error(request, "Course title is required.")
            return redirect("courses:teacher_home")

        # Validate category
        valid_categories = {c[0] for c in Course.CATEGORY_CHOICES}
        if category not in valid_categories:
            category = Course.CATEGORY_GENERAL

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
                course_id=course_id_input or None,  # ✅ None if empty
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
                    uploaded_by=request.user
                )

        messages.success(request, "Course created successfully.")
        return redirect("courses:teacher_home")

    return render(request, "courses/course_create.html", {
        "category_choices": Course.CATEGORY_CHOICES
    })


@login_required
def course_detail(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    is_teacher = (user.role == user.Role.TEACHER)
    is_student = (user.role == user.Role.STUDENT)

    can_view = False
    if is_teacher:
        can_view = Teaching.objects.filter(course=course, teacher=user).exists()
    elif is_student:
        can_view = Enrollment.objects.filter(course=course, student=user).exists()

    if not can_view:
        return HttpResponseForbidden("You don't have access to this course.")

    # Instructor (first teacher linked)
    instructor = (
        Teaching.objects.filter(course=course)
        .select_related("teacher")
        .first()
    )
    instructor_user = instructor.teacher if instructor else None

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

    context = {
        "course": course,
        "instructor_user": instructor_user,
        "enrollments": enrollments,
        "enrollment_count": enrollment_count,
        "avg_progress": avg_progress,
        "materials": materials,
        "materials_count": materials.count(),
        "is_teacher_view": is_teacher and Teaching.objects.filter(course=course, teacher=user).exists(),
    }
    return render(request, "courses/course_detail.html", context)


@login_required
def course_manage(request, course_id: int):
    """
    Manage a course (teacher-only):
    - Update course fields (including optional course_id)
    - Upload new materials
    - Delete materials
    """
    user = request.user
    if user.role != user.Role.TEACHER:
        return HttpResponseForbidden("Teachers only")

    course = get_object_or_404(Course, id=course_id)

    # Only the teacher who teaches this course can manage it
    if not Teaching.objects.filter(course=course, teacher=user).exists():
        return HttpResponseForbidden("You don't have access to manage this course.")

    COURSE_ID_RE = re.compile(r"^[A-Z0-9_-]+$")

    if request.method == "POST":
        # ===== Delete a material (optional) =====
        delete_material_id = (request.POST.get("delete_material_id") or "").strip()
        if delete_material_id:
            mat = CourseMaterial.objects.filter(id=delete_material_id, course=course).first()
            if mat:
                mat.delete()
                messages.success(request, "Material removed.")
            return redirect("courses:manage", course_id=course.id)

        # ===== Update course fields =====
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        category = (request.POST.get("category") or Course.CATEGORY_GENERAL).strip()
        duration = (request.POST.get("duration") or "").strip()

        max_students_raw = (request.POST.get("max_students") or "").strip()
        max_students = None
        if max_students_raw:
            try:
                max_students = int(max_students_raw)
                if max_students <= 0:
                    max_students = None
            except ValueError:
                max_students = None

        course_id_input = (request.POST.get("course_id") or "").strip().upper()

        if not title:
            messages.error(request, "Course title is required.")
            return redirect("courses:manage", course_id=course.id)

        valid_categories = {c[0] for c in Course.CATEGORY_CHOICES}
        if category not in valid_categories:
            category = Course.CATEGORY_GENERAL

        # Validate optional course_id
        if course_id_input:
            if len(course_id_input) > 20:
                messages.error(request, "Course ID must be 20 characters or fewer.")
                return redirect("courses:manage", course_id=course.id)

            if not COURSE_ID_RE.match(course_id_input):
                messages.error(request, "Course ID can only contain A–Z, 0–9, hyphen (-), underscore (_).")
                return redirect("courses:manage", course_id=course.id)

            # Unique check excluding this course
            if Course.objects.filter(course_id=course_id_input).exclude(id=course.id).exists():
                messages.error(request, f"Course ID '{course_id_input}' is already in use.")
                return redirect("courses:manage", course_id=course.id)

        # Save changes
        course.title = title
        course.description = description
        course.category = category
        course.duration = duration
        course.max_students = max_students
        course.course_id = course_id_input or None
        course.save()

        # ===== Upload materials =====
        files = request.FILES.getlist("materials")
        for f in files:
            CourseMaterial.objects.create(
                course=course,
                file=f,
                uploaded_by=user
            )

        messages.success(request, "Course updated successfully.")
        return redirect("courses:manage", course_id=course.id)

    # GET
    materials = CourseMaterial.objects.filter(course=course).order_by("-uploaded_at")
    enrollment_count = Enrollment.objects.filter(course=course).count()

    context = {
        "course": course,
        "materials": materials,
        "enrollment_count": enrollment_count,
        "category_choices": Course.CATEGORY_CHOICES,
    }
    return render(request, "courses/course_manage.html", context)


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
        "enrolled_count": enrolled_count,
        "deadlines": deadlines,
        "show_past": show_past,
        "updates": status_updates,
        "form": status_form,
    }

    return render(request, "courses/student_home.html", context)

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
