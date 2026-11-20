"""
Role-Based Access Control Decorators and Mixins.
Enforces group-level permissions with HTTP 403 PermissionDenied on violation.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    """
    View decorator that verifies the authenticated user belongs to at least one
    of the specified role groups (or is a superuser).
    Unauthenticated requests redirect to login.
    Authenticated requests with mismatched roles raise PermissionDenied (HTTP 403).
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_groups = set(request.user.groups.values_list("name", flat=True))
            if any(role in user_groups for role in allowed_roles):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied(
                f"Access denied. User '{request.user.username}' lacks required role(s): {allowed_roles}."
            )

        return _wrapped_view

    return decorator


class RoleRequiredMixin(AccessMixin):
    """
    CBV AccessMixin enforcing role membership.
    Raises PermissionDenied (HTTP 403) for authenticated users lacking the required role.
    """

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        user_groups = set(request.user.groups.values_list("name", flat=True))
        if any(role in user_groups for role in self.allowed_roles):
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied("Access denied. Insufficient role permissions.")
