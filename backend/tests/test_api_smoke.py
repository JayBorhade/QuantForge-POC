"""Integration smoke tests for the FastAPI application lifecycle.

Run explicitly with QUANTFORGE_RUN_INTEGRATION_TESTS=1 and a disposable test
PostgreSQL database configured through DATABASE_URL. These tests are skipped
during the fast unit-test suite so local unit tests do not require a database.
"""
import os
import unittest


@unittest.skipUnless(
    os.getenv("QUANTFORGE_RUN_INTEGRATION_TESTS") == "1",
    "Set QUANTFORGE_RUN_INTEGRATION_TESTS=1 to run database-backed API smoke tests",
)
class ApiStartupSmokeTests(unittest.TestCase):
    def test_application_starts_and_health_endpoints_respond(self):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            health = client.get("/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["status"], "healthy")

            root = client.get("/")
            self.assertEqual(root.status_code, 200)
            self.assertEqual(root.json()["name"], "QuantForge")
            self.assertIn("tagline", root.json())


if __name__ == "__main__":
    unittest.main()
