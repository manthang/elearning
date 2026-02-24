from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

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
# Enrollments (remove)
# =========================
@login_required
@require_POST
def enrollment_remove(request, course_id, enrollment_id):
    course, resp = _get_course_for_teacher_or_403(request, course_id)
    if resp:
        return resp

    deleted, _ = Enrollment.objects.filter(id=enrollment_id, course=course).delete()
    if deleted:
        messages.success(request, "Student removed from the course.")
    else:
        messages.error(request, "Enrollment not found.")
    return redirect("courses:course_detail", course_id=course.id)
