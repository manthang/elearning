from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("student/", views.student_home, name="student_home"),
    path("create/", views.course_create, name="create"),
    path("enrol/<int:course_id>/", views.enrol_course, name="enrol"),
    path("feedback/<int:course_id>/", views.leave_feedback, name="feedback"),
]
