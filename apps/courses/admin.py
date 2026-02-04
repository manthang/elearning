from django.contrib import admin
from .models import *

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_id", "title")
    search_fields = ("course_id", "title")

@admin.register(Teaching)
class TeachingAdmin(admin.ModelAdmin):
    list_display = ("teacher", "course")
    list_filter = ("teacher",)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "progress", "grade")
    list_filter = ("grade",)

@admin.register(CourseFeedback)
class CourseFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "student",
        "rating",
        "created_at",
    )

    list_filter = (
        "rating",
        "course",
    )

    search_fields = (
        "course__title",
        "student__username",
        "student__full_name",
        "comment",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("-created_at",)


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "due_at")
    list_filter = ("course",)
    search_fields = ("title", "course__title")