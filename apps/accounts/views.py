"""
Authentication, Role-Based Redirection, Role Landings, and Healthcheck Views.
"""

import logging

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import connection
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import role_required

logger = logging.getLogger(__name__)

# Role to landing page route mapping
ROLE_LANDING_PAGES = {
    "salesman": "/salesman/",
    "admin_desk": "/admin-desk/",
    "production": "/production/",
    "accountant": "/reports/",
    "owner": "/dashboard/",
}


def login_view(request):
    """
    Renders login view or processes login submission.
    Redirects authenticated users to their respective role landing page.
    """
    if request.user.is_authenticated:
        return redirect("accounts:role_redirect")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect("accounts:role_redirect")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "public/login.html",
        {
            "form": form,
            "page_title": "Sign In | Kaveri Foods",
            "demo_mode": getattr(settings, "DEMO_MODE", False),
        },
    )


@require_POST
def logout_view(request):
    """
    POST-only logout endpoint adhering to the data-logout form contract.
    Rejects GET requests with HTTP 405 Method Not Allowed.
    """
    auth_logout(request)
    return redirect("accounts:login")


@login_required
def role_redirect_view(request):
    """
    Redirects an authenticated user to their role-specific landing screen.
    """
    user = request.user
    if user.is_superuser:
        return redirect("/admin-desk/")

    user_groups = set(user.groups.values_list("name", flat=True))

    for role, target_url in ROLE_LANDING_PAGES.items():
        if role in user_groups:
            return HttpResponseRedirect(target_url)

    return redirect("/")


def _render_role_landing(request, role_code: str, role_display: str, role_description: str):
    """Internal helper to render consistent workspace shells for authenticated role groups."""
    return render(
        request,
        "roles/landing.html",
        {
            "role_code": role_code,
            "role_display": role_display,
            "role_description": role_description,
            "page_title": f"{role_display} | Kaveri Foods",
        },
    )


# Role-Protected Landing Views
@role_required("salesman", "admin_desk")
def salesman_landing_view(request):
    from apps.sales.views import salesman_workspace_view

    return salesman_workspace_view(request)


@role_required("admin_desk")
def admin_desk_landing_view(request):
    return _render_role_landing(
        request,
        role_code="admin_desk",
        role_display="Admin Desk Inbox",
        role_description="Factory order verification, dispatch generation, GST invoice printing, and stock allocation.",
    )


@role_required("production")
def production_landing_view(request):
    return _render_role_landing(
        request,
        role_code="production",
        role_display="Production Run Manager",
        role_description="Raw material batch issuance against recipe BOMs, yield tracking, variance calculations, and finished good packing.",
    )


@role_required("accountant")
def reports_landing_view(request):
    return _render_role_landing(
        request,
        role_code="accountant",
        role_display="Auditor & Accounting Reports",
        role_description="Monthly GST reports (GSTR-1, GSTR-3B summaries), immutable stock ledgers, production cost analyses, and debtor balances.",
    )


@role_required("owner")
def dashboard_landing_view(request):
    return _render_role_landing(
        request,
        role_code="owner",
        role_display="Owner Executive Dashboard",
        role_description="High-level operations overview, financial summaries, production run variance alerts, and collection status.",
    )


def healthz(request):
    """
    Production healthcheck endpoint.
    Executes a heartbeat query against the PostgreSQL database.
    Returns 200 OK or 503 Service Unavailable without exposing internal exception strings.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if not row or row[0] != 1:
                raise RuntimeError("Database heartbeat query returned unexpected result.")
        return JsonResponse({"status": "ok", "database": "connected"}, status=200)
    except Exception:
        logger.exception("Healthcheck failure: unable to communicate with database.")
        return JsonResponse({"status": "error"}, status=503)
