"""Regression tests for refresh-session revocation after credential resets."""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock

from app.services.auth import AuthService


class Result:
    def __init__(self, sessions):
        self.sessions = sessions

    def scalars(self):
        return self

    def all(self):
        return self.sessions


class AuthSessionRevocationTests(unittest.TestCase):
    def test_revoke_sessions_deactivates_every_active_session(self):
        user_id = uuid.uuid4()
        active_sessions = [
            type("Session", (), {"user_id": user_id, "is_active": True})(),
            type("Session", (), {"user_id": user_id, "is_active": True})(),
        ]
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(active_sessions))

        count = asyncio.run(AuthService.revoke_sessions(db, user_id))

        self.assertEqual(count, 2)
        self.assertTrue(all(session.is_active is False for session in active_sessions))
        db.execute.assert_awaited_once()

    def test_revoke_sessions_handles_no_active_sessions(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result([]))

        count = asyncio.run(AuthService.revoke_sessions(db, uuid.uuid4()))

        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
