"""Tests for safe email-verification resend behavior."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import BackgroundTasks

from app.api.routes.auth import resend_verification


class Result:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class ResendVerificationTests(unittest.TestCase):
    def test_unverified_user_receives_new_verification_task(self):
        user = SimpleNamespace(
            email="user@example.com",
            is_verified=False,
            email_verification_token="old-token",
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(user))
        tasks = BackgroundTasks()

        response = asyncio.run(
            resend_verification(SimpleNamespace(email="USER@example.com"), db, tasks)
        )

        self.assertIn("verification email has been sent", response["message"])
        self.assertNotEqual(user.email_verification_token, "old-token")
        self.assertEqual(len(tasks.tasks), 1)
        self.assertEqual(tasks.tasks[0].args, (user.email, user.email_verification_token))

    def test_verified_user_gets_generic_response_without_email(self):
        user = SimpleNamespace(
            email="user@example.com",
            is_verified=True,
            email_verification_token=None,
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(user))
        tasks = BackgroundTasks()

        response = asyncio.run(
            resend_verification(SimpleNamespace(email="user@example.com"), db, tasks)
        )

        self.assertIn("verification email has been sent", response["message"])
        self.assertEqual(len(tasks.tasks), 0)

    def test_unknown_email_gets_same_generic_response(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(None))
        tasks = BackgroundTasks()

        response = asyncio.run(
            resend_verification(SimpleNamespace(email="missing@example.com"), db, tasks)
        )

        self.assertIn("verification email has been sent", response["message"])
        self.assertEqual(len(tasks.tasks), 0)


if __name__ == "__main__":
    unittest.main()
