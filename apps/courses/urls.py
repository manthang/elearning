from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    # User Homepage
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("student/", views.student_home, name="student_home"),
    
    # Create a new Course
    path("courses/create/", views.course_create, name="course_create"),

    # Edit basic Course info
    path("courses/<int:course_id>/edit/", views.course_edit, name="course_edit"),

    # Enrollments (remove)
    path("courses/<int:course_id>/enrollments/<int:enrollment_id>/remove/",
         views.enrollment_remove, name="enrollment_remove"),

    # Materials
    path("courses/<int:course_id>/materials/upload/",
         views.material_upload, name="material_upload"),
    path("courses/<int:course_id>/materials/<int:material_id>/delete/",
         views.material_delete, name="material_delete"),

    # Deadlines
    path("courses/<int:course_id>/deadlines/add/",
         views.deadline_add, name="deadline_add"),
    path("courses/<int:course_id>/deadlines/<int:deadline_id>/edit/",
         views.deadline_edit, name="deadline_edit"),
    path("courses/<int:course_id>/deadlines/<int:deadline_id>/delete/",
         views.deadline_delete, name="deadline_delete"),

    # Student Actions
    path("courses/<int:course_id>/", views.course_detail, name="course_detail"),
    path("courses/<int:course_id>/enroll/", views.course_enroll, name="course_enroll"),
    path("courses/<int:course_id>/feedback/", views.course_feedback, name="course_feedback"),
]
