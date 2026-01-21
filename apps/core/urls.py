# apps/core/urls.py
from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home_redirect, name="home"),
    path("status/", views.status_feed, name="status_feed"),
]
