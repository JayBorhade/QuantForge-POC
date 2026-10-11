"""Regression tests for one-time authentication token storage."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

import pyotp

from app.core.security import hash_one_time_token
from app.services.auth import AuthService


class OneTimeTokenSecurityTests(unittest.TestCase):
    def test_token_digest_is_deterministic_and_not_plaintext(self):
        token = "test-reset-token-that-is-long-enough-for-testing"
        digest = hash_one_time_token(token)
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, token)
        self.assertEqual(hash_one_time_token(token), digest)

    def test_totp_time_step_cannot_be_replayed(self):
        secret = pyotp.random_base32()
        user = SimpleNamespace(two_factor_secret=secret, last_totp_step=None)
        code = pyotp.TOTP(secret).now()
        self.assertTrue(AuthService.verify_totp_once(user, code))
        self.assertFalse(AuthService.verify_totp_once(user, code))

    def test_different_tokens_have_different_digests(self):
        self.assertNotEqual(hash_one_time_token("token-a"), hash_one_time_token("token-b"))


if __name__ == "__main__":
    unittest.main()
