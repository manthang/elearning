from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Course,
    CourseMaterial,
    Teaching,
    Enrollment,
    CourseFeedback,
    Deadline,
)


# =========================
# Inline: Course materials
# =========================
class CourseMaterialInline(admin.TabularInline):
    model = CourseMaterial
    extra = 0
    fields = ("file", "original_name", "uploaded_by", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    autocomplete_fields = ("uploaded_by",)


# =========================
# Course
# =========================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "course_id",
        "title",
        "category",
        "duration",
        "max_students",
        "created_at",
        "updated_at",
    )
    search_fields = ("course_id", "title", "description")
    list_filter = ("category", "created_at", "updated_at")
    ordering = ("-updated_at", "title")
    readonly_fields = ("created_at", "updated_at")
    inlines = (CourseMaterialInline,)

    fieldsets = (
        ("Course info", {
            "fields": (
                "course_id",
                "title",
                "description",
                "category",
                "duration",
                "max_students",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


# =========================
# Course Material (standalone)
# =========================
@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ("course", "original_name", "uploaded_by", "uploaded_at", "file_link")
    list_filter = ("uploaded_at", "course")
    search_fields = ("original_name", "course__title", "course__course_id")
    autocomplete_fields = ("course", "uploaded_by")
    readonly_fields = ("uploaded_at", "original_name")

    def file_link(self, obj):
        if not obj.file:
            return "-"
        return format_html('<a href="{}" target="_blank">Open</a>', obj.file.url)
    file_link.short_description = "File"


# =========================
# Teaching / Enrollment / Feedback / Deadline
# =========================
@admin.register(Teaching)
class TeachingAdmin(admin.ModelAdmin):
    list_display = ("teacher", "course")
    list_filter = ("teacher",)
    search_fields = ("teacher__username", "teacher__full_name", "course__title", "course__course_id")
    autocomplete_fields = ("teacher", "course")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "progress", "grade")
    list_filter = ("grade", "course")
    search_fields = ("student__username", "student__full_name", "course__title", "course__course_id")
    autocomplete_fields = ("student", "course")


@admin.register(CourseFeedback)
class CourseFeedbackAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "rating", "created_at")
    list_filter = ("rating", "course")
    search_fields = ("course__title", "student__username", "student__full_name", "comment")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    autocomplete_fields = ("course", "student")


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "due_at", "created_at")
    list_filter = ("course", "due_at")
    search_fields = ("title", "course__title", "course__course_id")
    ordering = ("due_at",)
    autocomplete_fields = ("course",)
    readonly_fields = ("created_at",)
