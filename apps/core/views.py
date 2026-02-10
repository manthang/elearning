from django.shortcuts import render, redirect


def home_redirect(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if request.user.role == request.user.Role.TEACHER:
        return redirect("courses:teacher_home")

    return redirect("courses:student_home")

