from django.contrib import admin
from .models import Deadline

@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "due_at", "created_by")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
