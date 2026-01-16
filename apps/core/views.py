from django.shortcuts import redirect

def home_redirect(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if request.user.role == "teacher":
        return redirect("courses:teacher_home")

    return redirect("courses:student_home")
