from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import Course, CourseFeedback

@login_required
def teacher_home(request):
    if request.user.role != "teacher":
        return HttpResponseForbidden("Teachers only")

    courses = Course.objects.filter(teacher=request.user)
    return render(request, "courses/teacher_home.html", {"courses": courses})


@login_required
def student_home(request):
    if request.user.role != "student":
        return HttpResponseForbidden("Students only")

    courses = request.user.courses_enrolled.all()
    return render(request, "courses/student_home.html", {"courses": courses})

@login_required
def course_create(request):
    if request.user.role != "teacher":
        return HttpResponseForbidden("Teachers only")

    if request.method == "POST":
        Course.objects.create(
            title=request.POST["title"],
            description=request.POST.get("description", ""),
            teacher=request.user,
        )
        return redirect("courses:teacher_home")

    return render(request, "courses/course_create.html")


@login_required
def enrol_course(request, course_id):
    if request.user.role != "student":
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)
    course.students.add(request.user)
    return redirect("courses:student_home")


@login_required
def leave_feedback(request, course_id):
    if request.user.role != "student":
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        CourseFeedback.objects.create(
            course=course,
            student=request.user,
            comment=request.POST["comment"],
            rating=request.POST.get("rating", 5),
        )
        return redirect("courses:student_home")

    return render(request, "courses/feedback.html", {"course": course})
