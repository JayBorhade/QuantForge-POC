"""Regression tests for signed CSRF tokens and exact exemptions."""
import unittest

from app.core.csrf import _is_valid_signed_token, generate_csrf_token, is_csrf_exempt

class CsrfTokenTests(unittest.TestCase):
    def test_generated_token_has_valid_signature(self):
        token = generate_csrf_token()
        self.assertTrue(_is_valid_signed_token(token))

    def test_forged_or_modified_token_is_rejected(self):
        token = generate_csrf_token()
        self.assertFalse(_is_valid_signed_token("attacker-forged-token"))
        self.assertFalse(_is_valid_signed_token(token + "tampered"))

    def test_csrf_exemptions_are_exact(self):
        self.assertTrue(is_csrf_exempt("/api/v1/auth/login"))
        self.assertFalse(is_csrf_exempt("/api/v1/auth/refresh"))
        self.assertFalse(is_csrf_exempt("/api/v1/auth/resend-verification"))
        self.assertFalse(is_csrf_exempt("/api/v1/auth/login-export"))
        self.assertFalse(is_csrf_exempt("/api/v1/auth/reset-password-extra"))

if __name__ == "__main__":
    unittest.main()
