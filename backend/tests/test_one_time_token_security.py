"""Regression tests for one-time authentication token storage."""
import unittest

from app.core.security import hash_one_time_token


class OneTimeTokenSecurityTests(unittest.TestCase):
    def test_token_digest_is_deterministic_and_not_plaintext(self):
        token = "test-reset-token-that-is-long-enough-for-testing"
        digest = hash_one_time_token(token)
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, token)
        self.assertEqual(hash_one_time_token(token), digest)

    def test_different_tokens_have_different_digests(self):
        self.assertNotEqual(hash_one_time_token("token-a"), hash_one_time_token("token-b"))


if __name__ == "__main__":
    unittest.main()
