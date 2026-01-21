from django.contrib import admin
from .models import *

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_id", "title", "department")
    search_fields = ("course_id", "title")
    list_filter = ("department",)

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("course", "semester", "year")
    list_filter = ("semester", "year")

@admin.register(Teaching)
class TeachingAdmin(admin.ModelAdmin):
    list_display = ("teacher", "section")
    list_filter = ("teacher",)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "section", "progress", "grade")
    list_filter = ("grade",)

@admin.register(CourseFeedback)
class CourseFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "section",
        "rating",
        "created_at",
    )

    list_filter = (
        "rating",
        "section__course",
    )

    search_fields = (
        "student__username",
        "section__course__title",
    )

    ordering = ("-created_at",)
