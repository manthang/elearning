from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("student/", views.student_home, name="student_home"),
    path("create/", views.course_create, name="course_create"),
    path(
        "courses/<int:course_id>/enroll/",
        views.course_enroll,
        name="course_enroll",
    ),
    path(
        "courses/<int:course_id>/continue/",
        views.course_continue,
        name="course_continue",
    ),
    path(
        "courses/<int:course_id>/feedback/",
        views.course_feedback,
        name="course_feedback",
    ),

]
