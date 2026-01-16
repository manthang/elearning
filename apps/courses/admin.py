from django.contrib import admin
from .models import Course, CourseFeedback

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "created_at")
    search_fields = ("title", "teacher__username")
    filter_horizontal = ("students",)

@admin.register(CourseFeedback)
class CourseFeedbackAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "rating", "created_at")
