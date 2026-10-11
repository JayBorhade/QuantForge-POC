"""Tests for email-verification gates on sensitive operations."""

import asyncio
import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.deps import get_current_admin, get_verified_user
from app.models.user import UserRole


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

    def test_admin_without_mfa_is_rejected(self):
        user = SimpleNamespace(role=UserRole.ADMIN, two_factor_enabled=False)
        with self.assertRaises(HTTPException) as error:
            asyncio.run(get_current_admin(user))
        self.assertEqual(error.exception.status_code, 403)
        self.assertIn("multi-factor", error.exception.detail)

    def test_admin_with_mfa_is_allowed(self):
        user = SimpleNamespace(role=UserRole.ADMIN, two_factor_enabled=True)
        self.assertIs(asyncio.run(get_current_admin(user)), user)

    def test_non_admin_is_rejected_even_with_mfa(self):
        user = SimpleNamespace(role=UserRole.USER, two_factor_enabled=True)
        with self.assertRaises(HTTPException) as error:
            asyncio.run(get_current_admin(user))
        self.assertEqual(error.exception.status_code, 403)

if __name__ == "__main__":
    unittest.main()
