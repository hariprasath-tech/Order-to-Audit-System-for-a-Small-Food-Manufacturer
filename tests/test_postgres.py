"""
PostgreSQL-specific tests requiring a live PostgreSQL 16+ database engine.
Skips explicitly when test suite is executed against SQLite.
"""

import pytest
from django.db import connection


@pytest.mark.requires_postgres
def test_postgres_engine_and_server_version():
    """
    Verifies that the active database connection is PostgreSQL 16+.
    Skips loudly when running on SQLite.
    """
    assert connection.vendor == "postgresql", f"Expected 'postgresql', got '{connection.vendor}'"

    # Server version integer (e.g. 160001 for PostgreSQL 16.1)
    pg_version = getattr(connection, "pg_version", None)
    if pg_version is None and hasattr(connection, "connection") and connection.connection:
        pg_version = getattr(connection.connection.info, "server_version", 0)

    assert pg_version is not None and pg_version >= 160000, (
        f"PostgreSQL 16+ is required for immutable ledger triggers and locking (got {pg_version})."
    )
