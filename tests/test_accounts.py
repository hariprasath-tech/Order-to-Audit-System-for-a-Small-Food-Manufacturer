"""
Unit tests for Role-Based Access Control, Authentication, Role Landings, and Demo Users.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings

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

        self.production_user = User.objects.create_user(
            username="prod_supervisor", password="Password123"
        )
        self.production_user.groups.add(self.groups["production"])

        self.accountant_user = User.objects.create_user(
            username="factory_accountant", password="Password123"
        )
        self.accountant_user.groups.add(self.groups["accountant"])

        self.owner_user = User.objects.create_user(username="factory_owner", password="Password123")
        self.owner_user.groups.add(self.groups["owner"])

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

        request.user = self.production_user
        response = role_redirect_view(request)
        assert response.status_code == 302
        assert response.url == "/production/"

        request.user = self.accountant_user
        response = role_redirect_view(request)
        assert response.status_code == 302
        assert response.url == "/reports/"

        request.user = self.owner_user
        response = role_redirect_view(request)
        assert response.status_code == 302
        assert response.url == "/dashboard/"

    def test_post_only_logout(self):
        """Logout endpoint must reject GET with 405 and succeed on POST."""
        get_response = self.client.get("/accounts/logout/")
        assert get_response.status_code == 405

        self.client.login(username="sales_rep", password="Password123")
        post_response = self.client.post("/accounts/logout/")
        assert post_response.status_code == 302
        assert post_response.url == "/accounts/login/"

    def test_login_page_renders_form(self):
        """Login page must render working username and password form."""
        response = self.client.get("/accounts/login/")
        assert response.status_code == 200
        assert "username" in response.content.decode()
        assert "password" in response.content.decode()

    @override_settings(DEMO_MODE=True)
    def test_login_page_renders_demo_hints_when_demo_mode_true(self):
        """When DEMO_MODE is True, login page renders the demo accounts hint box."""
        response = self.client.get("/accounts/login/")
        assert response.status_code == 200
        assert "Role Test Logins" in response.content.decode()
        assert "salesman_a" in response.content.decode()

    @override_settings(DEMO_MODE=False)
    def test_login_page_hides_demo_hints_when_demo_mode_false(self):
        """When DEMO_MODE is False, login page does not expose demo accounts hint box."""
        response = self.client.get("/accounts/login/")
        assert response.status_code == 200
        assert "Role Test Logins" not in response.content.decode()

    def test_role_landing_page_authorized_and_logout_form(self):
        """Authorized user gets 200 on their role workspace with data-logout sign out button."""
        self.client.login(username="sales_rep", password="Password123")
        response = self.client.get("/salesman/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Salesman Order Entry" in content
        assert "data-logout" in content

    def test_role_landing_page_unauthorized_raises_403(self):
        """User accessing wrong role workspace must be denied with HTTP 403."""
        self.client.login(username="sales_rep", password="Password123")
        # Salesman attempting to access production workspace
        response = self.client.get("/production/")
        assert response.status_code == 403

    def test_index_page_redirects_authenticated_user(self):
        """Authenticated user visiting / is redirected to accounts:role_redirect."""
        self.client.login(username="sales_rep", password="Password123")
        response = self.client.get("/")
        assert response.status_code == 302
        assert response.url == "/accounts/redirect/"

    def test_create_demo_users_command_idempotency(self):
        """Management command create_demo_users creates all 6 demo accounts and is safely idempotent."""
        expected_users = {
            "salesman_a": "salesman",
            "salesman_b": "salesman",
            "admin_user": "admin_desk",
            "production": "production",
            "accountant": "accountant",
            "owner": "owner",
        }

        # First execution: creates accounts
        call_command("create_demo_users")

        for username, expected_group in expected_users.items():
            user = User.objects.get(username=username)
            assert user.check_password("Demo@1234")
            assert user.groups.filter(name=expected_group).exists()

        # Second execution: updates/resets accounts without errors or duplicates
        call_command("create_demo_users")
        assert User.objects.filter(username__in=expected_users.keys()).count() == 6
