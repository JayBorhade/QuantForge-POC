"""Regression tests for JWT claim integrity."""

import unittest
from datetime import datetime, timezone

from app.core.security import create_access_token, decode_token


class AccessTokenSecurityTests(unittest.TestCase):
    def test_extra_claims_cannot_override_reserved_access_claims(self):
        token = create_access_token(
            "trusted-user",
            {
                "role": "trader",
                "sub": "attacker-controlled-user",
                "type": "refresh",
                "exp": 4102444800,
            },
        )

        claims = decode_token(token)
        self.assertIsNotNone(claims)
        assert claims is not None
        self.assertEqual(claims["sub"], "trusted-user")
        self.assertEqual(claims["type"], "access")
        self.assertEqual(claims["role"], "trader")
        self.assertLess(claims["exp"], 4102444800)

    def test_access_token_contains_expiration(self):
        claims = decode_token(create_access_token("user-123"))
        self.assertIsNotNone(claims)
        assert claims is not None
        self.assertGreater(claims["exp"], int(datetime.now(timezone.utc).timestamp()))


if __name__ == "__main__":
    unittest.main()
