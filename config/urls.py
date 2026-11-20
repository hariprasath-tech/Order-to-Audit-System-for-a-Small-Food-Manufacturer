"""
URL configuration for Order-to-Audit System.
Merges PWA Service Worker, offline fallback, public landing, healthcheck, accounts, and role landing routes.
"""

import os

from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import include, path
from django.views.decorators.cache import cache_control

from apps.accounts import views as account_views


@cache_control(max_age=0, no_cache=True, must_revalidate=True)
def service_worker_view(request):
    """
    Serves /sw.js directly from the root with header Service-Worker-Allowed: /.
    Uses django.contrib.staticfiles.finders.find('sw.js') so it works during development
    and falls back to STATIC_ROOT after collectstatic in production.
    """
    sw_path = finders.find("sw.js")
    if not sw_path and getattr(settings, "STATIC_ROOT", None):
        prod_sw_path = os.path.join(settings.STATIC_ROOT, "sw.js")
        if os.path.exists(prod_sw_path):
            sw_path = prod_sw_path

    if not sw_path or not os.path.exists(sw_path):
        raise Http404("Service Worker asset not found.")

    response = FileResponse(open(sw_path, "rb"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


def offline_fallback_view(request):
    """
    Renders the generic offline fallback template (precached by the Service Worker).
    """
    return render(request, "offline.html")


def index_view(request):
    """
    Public landing entry point.
    Redirects authenticated users to their role landing screen;
    renders landing_home.html with brand hero and sign-in button for anonymous visitors.
    """
    if request.user.is_authenticated:
        return redirect("accounts:role_redirect")

    return render(
        request,
        "public/landing_home.html",
        {
            "page_title": "Kaveri Foods | Order-to-Audit System",
        },
    )


urlpatterns = [
    # Healthcheck Endpoint (Docker Compose & Monitoring)
    path("healthz", account_views.healthz, name="root_healthz"),
    # Public Landing Page
    path("", index_view, name="index"),
    # Authentication & Accounts
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    # Role Landing Workspaces (protected via @role_required)
    path("salesman/", account_views.salesman_landing_view, name="salesman_landing"),
    path("salesman/", include("apps.sales.urls", namespace="salesman")),
    path("admin-desk/", account_views.admin_desk_landing_view, name="admin_desk_landing"),
    path("production/", account_views.production_landing_view, name="production_landing"),
    path("reports/", account_views.reports_landing_view, name="reports_landing"),
    path("dashboard/", account_views.dashboard_landing_view, name="dashboard_landing"),
    # PWA Service Worker served at domain root with Service-Worker-Allowed: /
    path("sw.js", service_worker_view, name="service_worker"),
    # PWA Offline Navigation Fallback
    path("offline/", offline_fallback_view, name="offline"),
    # Django Administration Interface
    path("admin/", admin.site.urls),
]
