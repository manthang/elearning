from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),

    path("accounts/search/", views.user_search, name="user_search"),
    path("accounts/<str:username>/", views.user_profile, name="user_profile"),
    path("accounts/me/edit/", views.edit_profile, name="edit_profile"),
]
