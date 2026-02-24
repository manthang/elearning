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
# Upload Materials
# =========================
@login_required
@require_POST
def material_upload(request, course_id):
    course, resp = _get_course_for_teacher_or_403(request, course_id)
    if resp:
        return resp

    # keep it flexible with name
    f = request.FILES.get("material") or request.FILES.get("file") or request.FILES.get("materials")
    if not f:
        messages.error(request, "Please choose a file to upload.")
        return redirect("courses:course_detail", course_id=course.id)

    CourseMaterial.objects.create(
        course=course,
        file=f,
        original_name=getattr(f, "name", "") or "",
        uploaded_by=request.user
    )
    messages.success(request, "Material uploaded.")
    return redirect("courses:course_detail", course_id=course.id)

# =========================
# Delete Materials
# =========================
@login_required
@require_POST
def material_delete(request, course_id, material_id):
    course, resp = _get_course_for_teacher_or_403(request, course_id)
    if resp:
        return resp

    deleted, _ = CourseMaterial.objects.filter(id=material_id, course=course).delete()
    if deleted:
        messages.success(request, "Material deleted.")
    else:
        messages.error(request, "Material not found.")
    return redirect("courses:course_detail", course_id=course.id)
