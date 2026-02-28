from ..utils import *

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
from django.urls import reverse

@login_required
def course_detail(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    # Which tab are we on? (Defaults to 'overview')
    current_tab = request.GET.get("tab", "overview")

    # --- COMMON DATA (Needed for Permissions and the Top Header) ---
    # Check roles
    is_teacher = (user.role == user.Role.TEACHER)
    is_student = (user.role == user.Role.STUDENT)
    is_teacher_view = is_teacher and Teaching.objects.filter(course=course, teacher=user).exists()

    # Determine the correct Dashboard URL
    if is_teacher:
        dashboard_url = reverse("courses:teacher_home")
    elif is_student:
        dashboard_url = reverse("courses:student_home")
    else:
        # Fallback just in case (e.g., an admin user)
        dashboard_url = "/"
    
    # Check Enrollment Status
    is_enrolled = False
    if is_student:
        is_enrolled = Enrollment.objects.filter(student=user, course=course).exists()

    # Fetch all feedback data
    feedback_data = get_course_feedback_data(course)

    # --- COMMON DATA (Always passed for the Header) ---
    enrollment_count = Enrollment.objects.filter(course=course).count()
    instructor = Teaching.objects.filter(course=course).select_related("teacher").first()

    context = {
        "course": course,
        "current_tab": current_tab,
        "dashboard_url": dashboard_url,
        "is_teacher_view": is_teacher_view,
        "instructor_user": instructor.teacher if instructor else None,
        "is_enrolled": is_enrolled,
        "enrollment_count": enrollment_count,
        "total_reviews": feedback_data['total_reviews'],
        "avg_rating": feedback_data['avg_rating'],
        "star_display": feedback_data['star_display'],
    }

    # --- CONDITIONAL DATA (Only runs what is needed!) ---
    
    if current_tab == "overview":
        # Maybe fetch course syllabus or recent announcements here
        pass

    elif current_tab == "students" and is_teacher_view:
        # Only fetch the heavy student list and calculate progress if on this tab
        enrollments = Enrollment.objects.filter(course=course).select_related("student").order_by("-id")
        avg_progress = enrollments.aggregate(a=Avg("progress"))["a"] or 0
        
        context["enrollments"] = enrollments
        context["avg_progress"] = int(round(avg_progress))

    elif current_tab == "materials":
        # Only fetch files if on the materials tab
        context["materials"] = CourseMaterial.objects.filter(course=course).order_by("-uploaded_at")

    elif current_tab == "deadlines":
        # Only fetch deadlines if on the deadlines tab
        context["deadlines"] = Deadline.objects.filter(course=course).order_by("due_at")

    elif current_tab == "feedback":
        context["reviews"] = feedback_data['reviews']
        context["rating_stats"] = feedback_data['rating_stats']

    # Render the single main shell
    return render(request, "courses/course_detail/main.html", context)