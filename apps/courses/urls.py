from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    # User Homepage
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("student/", views.student_home, name="student_home"),
    
    # Teacher Management
    path("courses/create/", views.course_create, name="course_create"),
    path("courses/<int:course_id>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:course_id>/manage/", views.course_manage, name="course_manage"),
    path("courses/<int:course_id>/", views.course_detail, name="course_detail"),

    # Student Actions
    path("courses/<int:course_id>/enroll/", views.course_enroll, name="course_enroll"),
    path("courses/<int:course_id>/feedback/", views.course_feedback, name="course_feedback"),
]
