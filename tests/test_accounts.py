"""
Unit tests for Role-Based Access Control, Authentication, and Role Routing.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase

from apps.accounts.decorators import role_required
from apps.accounts.views import role_redirect_view

User = get_user_model()


@role_required("admin_desk")
def sample_admin_view(request):
    return HttpResponse("Admin Access Granted", status=200)


@role_required("salesman", "admin_desk")
def sample_multi_role_view(request):
    return HttpResponse("Multi Role Access Granted", status=200)


@pytest.mark.django_db
class TestAccountsRBAC(TestCase):
    """Verifies group creation, role_required protection, and role redirections."""

    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

        # Ensure role groups exist
        self.roles = ["salesman", "admin_desk", "production", "accountant", "owner"]
        self.groups = {role: Group.objects.get_or_create(name=role)[0] for role in self.roles}

        # Create test users
        self.salesman = User.objects.create_user(username="sales_rep", password="Password123")
        self.salesman.groups.add(self.groups["salesman"])

        self.admin_user = User.objects.create_user(username="factory_admin", password="Password123")
        self.admin_user.groups.add(self.groups["admin_desk"])

        self.unassigned = User.objects.create_user(username="no_role_user", password="Password123")

    def test_role_required_permits_matching_role(self):
        """User with required role must be allowed to access view."""
        request = self.factory.get("/admin-desk/")
        request.user = self.admin_user

        response = sample_admin_view(request)
        assert response.status_code == 200
        assert response.content.decode() == "Admin Access Granted"

    def test_role_required_denies_wrong_role(self):
        """User with wrong role must be denied with PermissionDenied (HTTP 403)."""
        request = self.factory.get("/admin-desk/")
        request.user = self.salesman

        with pytest.raises(PermissionDenied):
            sample_admin_view(request)

    def test_role_required_permits_any_of_multiple_roles(self):
        """Multi-role view allows any authorized group."""
        request1 = self.factory.get("/order-entry/")
        request1.user = self.salesman
        assert sample_multi_role_view(request1).status_code == 200

        request2 = self.factory.get("/order-entry/")
        request2.user = self.admin_user
        assert sample_multi_role_view(request2).status_code == 200

        request3 = self.factory.get("/order-entry/")
        request3.user = self.unassigned
        with pytest.raises(PermissionDenied):
            sample_multi_role_view(request3)

    def test_role_redirect_view_routes(self):
        """Authenticated users must be redirected to their role landing screen."""
        request = self.factory.get("/accounts/redirect/")
        request.user = self.salesman
        response = role_redirect_view(request)
        assert response.status_code == 302
        assert response.url == "/salesman/"

        request.user = self.admin_user
        response = role_redirect_view(request)
        assert response.status_code == 302
        assert response.url == "/admin-desk/"

    def test_post_only_logout(self):
        """Logout endpoint must reject GET with 405 and succeed on POST."""
        get_response = self.client.get("/accounts/logout/")
        assert get_response.status_code == 405

        self.client.login(username="sales_rep", password="Password123")
        post_response = self.client.post("/accounts/logout/")
        assert post_response.status_code == 302
        assert post_response.url == "/accounts/login/"
