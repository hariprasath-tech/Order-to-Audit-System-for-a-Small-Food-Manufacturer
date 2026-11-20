"""URL routing for accounts application."""

from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("redirect/", views.role_redirect_view, name="role_redirect"),
    path("healthz", views.healthz, name="healthz"),
]
