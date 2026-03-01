from django.urls import path
from . import views

app_name = "status"

urlpatterns = [
    path("post/", views.post_status, name="post"),
    path("delete/<int:status_id>/", views.delete_status, name="delete"),
    path("like/<int:status_id>/", views.toggle_like, name="toggle_like"),
    path("comment/<int:status_id>/", views.post_comment, name="post_comment"),
    path("comment/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),
]