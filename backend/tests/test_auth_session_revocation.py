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


    def test_password_reset_revokes_sessions(self):
        from datetime import datetime, timedelta, timezone
        from types import SimpleNamespace
        from unittest.mock import patch

        from app.api.routes.auth import reset_password

        user = SimpleNamespace(
            id=uuid.uuid4(),
            hashed_password="old-hash",
            password_reset_token="valid-token",
            password_reset_expires=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=type(
            "UserResult", (), {"scalar_one_or_none": lambda self: user}
        )())
        data = SimpleNamespace(token="valid-token", password="NewSecurePassword123!")
        request = SimpleNamespace()

        async def run_reset():
            with patch("app.api.routes.auth.AuthService.revoke_sessions", new_callable=AsyncMock) as revoke:
                with patch("app.api.routes.auth.log_audit", new_callable=AsyncMock):
                    result = await reset_password(data, db, request)
                    revoke.assert_awaited_once_with(db, user.id)
                    return result

        response = asyncio.run(run_reset())
        self.assertEqual(response["message"], "Password reset successfully")
        self.assertIsNone(user.password_reset_token)
        self.assertIsNone(user.password_reset_expires)
        self.assertNotEqual(user.hashed_password, "old-hash")


if __name__ == "__main__":
    unittest.main()
