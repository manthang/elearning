
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
from django.views.decorators.http import require_POST

from .models import *
from .forms import *

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


# =========================
# Create New Course
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
# Get Course Detail
# =========================
@login_required
def course_detail(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    is_teacher = (user.role == user.Role.TEACHER)
    is_student = (user.role == user.Role.STUDENT)

    can_view = False
    if is_teacher:
        can_view = Teaching.objects.filter(course=course, teacher=user).exists()
        back_url = reverse("courses:teacher_home")
    elif is_student:
        can_view = Enrollment.objects.filter(course=course, student=user).exists()
        back_url = reverse("courses:student_home")

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
        "back_url": back_url,
    }
    return render(request, "courses/course_detail.html", context)


@login_required
def course_manage(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    # 🔒 Teachers who teach this course only
    is_teacher = (user.role == user.Role.TEACHER) and Teaching.objects.filter(course=course, teacher=user).exists()
    if not is_teacher:
        return HttpResponseForbidden("Teachers only")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # ---------- Students ----------
        if action == "remove_student":
            enrollment_id = (request.POST.get("enrollment_id") or "").strip()
            deleted, _ = Enrollment.objects.filter(id=enrollment_id, course=course).delete()
            if deleted:
                messages.success(request, "Student removed from the course.")
            else:
                messages.error(request, "Enrollment not found.")
            return redirect("courses:course_detail", course_id=course.id)

        # ---------- Materials ----------
        if action == "upload_material":
            f = request.FILES.get("material") or request.FILES.get("materials") or request.FILES.get("file")
            if not f:
                messages.error(request, "Please choose a file to upload.")
                return redirect("courses:course_detail", course_id=course.id)

            CourseMaterial.objects.create(
                course=course,
                file=f,
                original_name=getattr(f, "name", "") or "",
                uploaded_by=user
            )
            messages.success(request, "Material uploaded.")
            return redirect("courses:course_detail", course_id=course.id)

        if action == "delete_material":
            material_id = (request.POST.get("material_id") or "").strip()
            CourseMaterial.objects.filter(id=material_id, course=course).delete()
            messages.success(request, "Material deleted.")
            return redirect("courses:course_detail", course_id=course.id)

        # ---------- Deadlines ----------
        if action == "add_deadline":
            title = (request.POST.get("deadline_title") or "").strip()
            due_at_raw = (request.POST.get("deadline_due_at") or "").strip()
            description = (request.POST.get("deadline_description") or "").strip()

            if not title or not due_at_raw:
                messages.error(request, "Title and due date are required.")
                return redirect("courses:course_detail", course_id=course.id)

            try:
                dt = datetime.fromisoformat(due_at_raw)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
            except Exception:
                messages.error(request, "Invalid due date format.")
                return redirect("courses:course_detail", course_id=course.id)

            Deadline.objects.create(
                course=course,
                title=title,
                due_at=dt,
                description=description
            )
            messages.success(request, "Deadline added.")
            return redirect("courses:course_detail", course_id=course.id)

        if action == "update_deadline":
            deadline_id = (request.POST.get("deadline_id") or "").strip()
            title = (request.POST.get("deadline_title") or "").strip()
            due_at_raw = (request.POST.get("deadline_due_at") or "").strip()
            description = (request.POST.get("deadline_description") or "").strip()

            if not deadline_id:
                messages.error(request, "Deadline not found.")
                return redirect("courses:course_detail", course_id=course.id)

            dl = Deadline.objects.filter(id=deadline_id, course=course).first()
            if not dl:
                messages.error(request, "Deadline not found.")
                return redirect("courses:course_detail", course_id=course.id)

            if not title or not due_at_raw:
                messages.error(request, "Title and due date are required.")
                return redirect("courses:course_detail", course_id=course.id)

            try:
                dt = datetime.fromisoformat(due_at_raw)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
            except Exception:
                messages.error(request, "Invalid due date format.")
                return redirect("courses:course_detail", course_id=course.id)

            dl.title = title
            dl.due_at = dt
            dl.description = description
            dl.save()

            messages.success(request, "Deadline updated.")
            return redirect("courses:course_detail", course_id=course.id)

        if action == "delete_deadline":
            deadline_id = (request.POST.get("deadline_id") or "").strip()
            Deadline.objects.filter(id=deadline_id, course=course).delete()
            messages.success(request, "Deadline deleted.")
            return redirect("courses:course_detail", course_id=course.id)

        # Unknown action
        messages.error(request, "Invalid action.")
        return redirect("courses:course_detail", course_id=course.id)

    # For GET, just go back to detail (manage is POST-only in this design)
    return redirect("courses:course_detail", course_id=course.id)


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

