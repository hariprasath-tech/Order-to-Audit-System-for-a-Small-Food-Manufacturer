"""
Unit tests for the application healthcheck endpoint.
"""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_healthz_endpoint():
    """GET /healthz must return 200 OK and database status."""
    client = Client()
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
