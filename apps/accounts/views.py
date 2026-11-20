"""
Authentication, Role-Based Redirection, and Healthcheck Views.
"""

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import connection
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

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
        "public/login.html" if False else "base_public.html",
        {
            "form": form,
            "page_title": "Sign In | Kaveri Foods",
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


def healthz(request):
    """
    Production healthcheck endpoint.
    Executes a heartbeat query against the PostgreSQL database.
    Returns 200 OK or 503 Service Unavailable.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if not row or row[0] != 1:
                raise RuntimeError("Database heartbeat query returned unexpected result.")
        return JsonResponse({"status": "ok", "database": "connected"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "error", "database": str(e)}, status=503)
