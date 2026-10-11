"""Security response headers regression tests."""
import unittest
from fastapi.testclient import TestClient
from app.main import app

class SecurityHeaderTests(unittest.TestCase):
    def test_root_response_includes_security_headers(self):
        with TestClient(app) as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("strict-origin-when-cross-origin", response.headers["Referrer-Policy"])
        self.assertIn("camera=()", response.headers["Permissions-Policy"])

if __name__ == "__main__":
    unittest.main()
