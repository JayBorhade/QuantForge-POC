"""Phase 1 regression tests for CSRF, email logging and reset password policy."""

import unittest
from unittest.mock import patch
from types import SimpleNamespace

from app.core.csrf import validate_csrf
from app.schemas.auth import ResetPasswordRequest
from app.services.email import send_email


class PhaseOneSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_dev_email_fallback_does_not_log_body_or_succeed(self):
        fake_settings = SimpleNamespace(
            smtp_user="", smtp_password="", app_env="development"
        )
        with patch("app.services.email.settings", fake_settings), patch("app.services.email.logger") as logger:
            result = await send_email("person@example.com", "Reset", "secret-token-body")
        self.assertFalse(result)
        rendered = " ".join(str(call) for call in logger.mock_calls)
        self.assertNotIn("secret-token-body", rendered)

    def test_password_reset_enforces_signup_complexity(self):
        with self.assertRaises(ValueError):
            ResetPasswordRequest(token="x" * 40, password="lowercase123", confirm_password="lowercase123")
        with self.assertRaises(ValueError):
            ResetPasswordRequest(token="x" * 40, password="UPPERCASE123", confirm_password="UPPERCASE123")
        request = ResetPasswordRequest(token="x" * 40, password="SecurePass123", confirm_password="SecurePass123")
        self.assertEqual(request.password, "SecurePass123")

    def test_csrf_rejection_returns_json_403(self):
        request = SimpleNamespace(
            method="POST",
            url=SimpleNamespace(path="/api/v1/portfolios"),
            cookies={},
            headers={},
        )
        with patch("app.core.csrf.get_settings") as get_settings:
            get_settings.return_value = SimpleNamespace(csrf_enabled=True, api_v1_prefix="/api/v1", secret_key="test-secret")
            response = validate_csrf(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
