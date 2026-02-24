from datetime import datetime
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from ..models import *


# =========================
# Helper Functions
# =========================
def _get_course_for_teacher_or_403(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    is_teacher = (
        user.is_authenticated
        and user.role == user.Role.TEACHER
        and Teaching.objects.filter(course=course, teacher=user).exists()
    )
    if not is_teacher:
        return None, HttpResponseForbidden("Teachers only")
    return course, None


# =========================
# Deadlines (add, edit, delete)
# =========================
def _parse_due_at_or_none(due_at_raw: str):
    """
    Accepts HTML datetime-local string: 'YYYY-MM-DDTHH:MM' (or full ISO)
    Returns aware datetime or None.
    """
    due_at_raw = (due_at_raw or "").strip()
    if not due_at_raw:
        return None

    try:
        dt = datetime.fromisoformat(due_at_raw)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


@login_required
@require_POST
def deadline_add(request, course_id):
    course, resp = _get_course_for_teacher_or_403(request, course_id)
    if resp:
        return resp

    title = (request.POST.get("title") or request.POST.get("deadline_title") or "").strip()
    description = (request.POST.get("description") or request.POST.get("deadline_description") or "").strip()
    due_at_raw = request.POST.get("due_at") or request.POST.get("deadline_due_at") or ""

    dt = _parse_due_at_or_none(due_at_raw)
    if not title or not dt:
        messages.error(request, "Title and due date are required.")
        return redirect("courses:course_detail", course_id=course.id)

    Deadline.objects.create(course=course, title=title, description=description, due_at=dt)
    messages.success(request, "Deadline added.")
    return redirect("courses:course_detail", course_id=course.id)


@login_required
@require_POST
def deadline_edit(request, course_id, deadline_id):
    course, resp = _get_course_for_teacher_or_403(request, course_id)
    if resp:
        return resp

    dl = get_object_or_404(Deadline, id=deadline_id, course=course)

    title = (request.POST.get("title") or request.POST.get("deadline_title") or "").strip()
    description = (request.POST.get("description") or request.POST.get("deadline_description") or "").strip()
    due_at_raw = request.POST.get("due_at") or request.POST.get("deadline_due_at") or ""

    dt = _parse_due_at_or_none(due_at_raw)
    if not title or not dt:
        messages.error(request, "Title and due date are required.")
        return redirect("courses:course_detail", course_id=course.id)

    dl.title = title
    dl.description = description
    dl.due_at = dt
    dl.save()

    messages.success(request, "Deadline updated.")
    return redirect("courses:course_detail", course_id=course.id)


@login_required
@require_POST
def deadline_delete(request, course_id, deadline_id):
    course, resp = _get_course_for_teacher_or_403(request, course_id)
    if resp:
        return resp

    deleted, _ = Deadline.objects.filter(id=deadline_id, course=course).delete()
    if deleted:
        messages.success(request, "Deadline deleted.")
    else:
        messages.error(request, "Deadline not found.")
    return redirect("courses:course_detail", course_id=course.id)