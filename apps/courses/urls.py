from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [    
    # Create a new Course
    path("create/", views.course_create, name="course_create"),

    # Edit basic Course info
    path("<int:course_id>/edit/", views.course_edit, name="course_edit"),

    # Enrollments (remove)
    path("<int:course_id>/enrollments/<int:enrollment_id>/remove/",
         views.enrollment_remove, name="enrollment_remove"),

    # Materials
    path("<int:course_id>/materials/upload/",
         views.material_upload, name="material_upload"),
    path("<int:course_id>/materials/<int:material_id>/delete/",
         views.material_delete, name="material_delete"),

    # Deadlines
    path("<int:course_id>/deadlines/add/",
         views.deadline_add, name="deadline_add"),
    path("<int:course_id>/deadlines/<int:deadline_id>/edit/",
         views.deadline_edit, name="deadline_edit"),
    path("<int:course_id>/deadlines/<int:deadline_id>/delete/",
         views.deadline_delete, name="deadline_delete"),

    # Student Actions
    path("<int:course_id>/", views.course_detail, name="course_detail"),
    path("<int:course_id>/enroll/", views.course_enroll, name="course_enroll"),

    # Feedback for a Course: GET to retrieve, POST to create
    path("<int:course_id>/feedback/", views.course_feedback, name="course_feedback"),

    # Course Search
    path("search/", views.course_search, name="course_search"),
]
