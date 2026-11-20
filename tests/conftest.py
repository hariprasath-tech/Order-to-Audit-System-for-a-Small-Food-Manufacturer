"""
Pytest configuration and environment defaults for test execution.
"""

import os
import pytest
from django.db import connection

# Ensure required environment variables exist for test execution
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-execution-12345")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("DEFAULT_VARIANCE_TOLERANCE", "3.00")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_postgres: mark test as requiring a live PostgreSQL database"
    )


@pytest.fixture(autouse=True)
def skip_if_not_postgres(request):
    """
    If a test is marked with @pytest.mark.requires_postgres,
    ensure the current database engine is postgresql; otherwise skip loudly on SQLite.
    """
    if request.node.get_closest_marker("requires_postgres"):
        engine = connection.settings_dict.get("ENGINE", "")
        if "postgresql" not in engine:
            pytest.skip(
                f"Test requires PostgreSQL (current engine: {engine}). Run inside Docker container."
            )
