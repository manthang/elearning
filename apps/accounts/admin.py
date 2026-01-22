from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "full_name",
        "email",
        "role",
        "is_staff",
        "is_active",
    )

    list_filter = ("role", "is_staff", "is_active")

    fieldsets = UserAdmin.fieldsets + (
        ("Additional info", {
            "fields": (
                "full_name",
                "role",
                "location",
                "department",
                "profile_photo",
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Additional info", {
            "fields": ("role",),
        }),
    )
