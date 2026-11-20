"""
Configuration and Root Routing Test Suite for Order-to-Audit System.
Verifies directory bindings, statutory settings, HTTPS flags, and PWA endpoints.
"""

from decimal import Decimal

from django.conf import settings
from django.test import Client, SimpleTestCase


class ConfigurationTests(SimpleTestCase):
    """Verifies core Django settings and file directory bindings."""

    def test_staticfiles_and_templates_directories(self):
        """Rule 2 verification: STATICFILES_DIRS binds root static/, TEMPLATES binds root templates/."""
        base_dir = settings.BASE_DIR
        static_dir = base_dir / "static"
        template_dir = base_dir / "templates"

        self.assertIn(
            static_dir, settings.STATICFILES_DIRS, f"STATICFILES_DIRS must include {static_dir}"
        )

        template_dirs = settings.TEMPLATES[0]["DIRS"]
        self.assertIn(template_dir, template_dirs, f"TEMPLATES DIRS must include {template_dir}")

    def test_statutory_gst_and_variance_settings(self):
        """Verifies Tamil Nadu state code 33, GSTIN, and Decimal variance tolerance."""
        self.assertEqual(settings.SELLER_STATE_CODE, "33")
        self.assertEqual(settings.SELLER_GSTIN, "33AAAAA0000A1Z5")
        self.assertEqual(settings.DEFAULT_VARIANCE_TOLERANCE, Decimal("3.00"))
        self.assertIsInstance(settings.DEFAULT_VARIANCE_TOLERANCE, Decimal)

    def test_https_and_csrf_settings(self):
        """Verifies USE_HTTPS and CSRF_TRUSTED_ORIGINS settings exist and behave correctly."""
        self.assertIsInstance(settings.USE_HTTPS, bool)
        self.assertIsInstance(settings.CSRF_TRUSTED_ORIGINS, list)


class RootRoutingTests(SimpleTestCase):
    """Verifies root routing, public landing, and PWA offline fallbacks."""

    def setUp(self):
        self.client = Client()

    def test_public_landing_page(self):
        """Root GET / returns 200 and contains brand identifier."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kaveri Foods")
        self.assertContains(response, "Order-to-Audit System")

    def test_service_worker_endpoint(self):
        """GET /sw.js returns 200 with Service-Worker-Allowed: / header."""
        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Service-Worker-Allowed"), "/")
        self.assertIn("javascript", response.headers.get("Content-Type", ""))

    def test_offline_fallback_page(self):
        """GET /offline/ returns 200 and renders the offline fallback template."""
        response = self.client.get("/offline/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You are currently offline")
        self.assertContains(response, "NETWORK_DISCONNECTED")
