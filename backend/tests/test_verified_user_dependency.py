"""Tests for email-verification gates on sensitive operations."""

import asyncio
import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.deps import get_verified_user


class VerifiedUserDependencyTests(unittest.TestCase):
    def test_verified_user_is_allowed(self):
        user = SimpleNamespace(is_verified=True)
        self.assertIs(asyncio.run(get_verified_user(user)), user)

    def test_unverified_user_is_rejected(self):
        user = SimpleNamespace(is_verified=False)
        with self.assertRaises(HTTPException) as error:
            asyncio.run(get_verified_user(user))
        self.assertEqual(error.exception.status_code, 403)
        self.assertIn("Verify your email", error.exception.detail)


if __name__ == "__main__":
    unittest.main()
