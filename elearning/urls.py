from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("courses/", include("apps.courses.urls")),
    # path("chat/", include("apps.chat.urls")),
]
