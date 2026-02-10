from django.urls import path
from . import views

app_name = "status"

urlpatterns = [
    path("post/", views.post_status, name="post"),
]
