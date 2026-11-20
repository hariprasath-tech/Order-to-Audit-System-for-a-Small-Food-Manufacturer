"""
Unit tests for the application healthcheck endpoint.
"""

from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.test import Client


@pytest.mark.django_db
def test_healthz_endpoint_success():
    """GET /healthz returns 200 OK and connected status when database is reachable."""
    client = Client()
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


@pytest.mark.django_db
def test_healthz_endpoint_failure_masks_details():
    """GET /healthz returns 503 and masks internal database exception details."""
    client = Client()
    with patch("django.db.connection.cursor", side_effect=DatabaseError("Sensitive credentials")):
        response = client.get("/healthz")
        assert response.status_code == 503
        data = response.json()
        assert data == {"status": "error"}
        assert "Sensitive credentials" not in str(data)
