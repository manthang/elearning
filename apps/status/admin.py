# accounts/admin.py

from django.contrib import admin
from .models import *


@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "author"
    )
