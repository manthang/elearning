from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Core app for home page redirect
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.courses.urls")),
    path("status/", include("apps.status.urls")),
    path("chat/", include("apps.chat.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
