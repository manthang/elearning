from django.urls import path
from . import views
from . import student_views

app_name = "courses"

urlpatterns = [
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("student/", views.student_home, name="student_home"),
    path("profile/update/", student_views.profile_update, name="profile_update"),
    path("create/", views.course_create, name="course_create"),
    path("<int:course_id>/", views.course_detail, name="detail"),
    path("<int:course_id>/edit/", views.course_edit, name="update_course_info"),
    path("<int:course_id>/manage/", views.course_manage, name="manage"),
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
