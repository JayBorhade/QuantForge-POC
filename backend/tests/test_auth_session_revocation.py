"""Regression tests for refresh-session revocation after credential resets."""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock

from fastapi import FastAPI, HTTPException
from starlette.requests import Request
from types import SimpleNamespace

from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.services.auth import AuthService
from app.core.rate_limit import limiter


def make_request(path: str) -> Request:
    app = FastAPI()
    app.state.limiter = limiter
    return Request({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": b"", "headers": [], "client": ("127.0.0.1", 12345), "server": ("testserver", 80), "app": app})


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
        request = make_request("/api/v1/auth/reset-password")

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



class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class SessionBoundAccessTokenTests(unittest.TestCase):
    def test_active_session_bound_access_token_is_accepted(self):
        user_id = uuid.uuid4()
        user = SimpleNamespace(id=user_id, is_active=True, is_banned=False)
        session = SimpleNamespace(is_active=True)
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[ScalarResult(session), ScalarResult(user)])
        request = SimpleNamespace(headers={})
        token = create_access_token(str(user_id), {"session_jti": "session-1"})

        resolved = asyncio.run(get_current_user(request, db, token))

        self.assertIs(resolved, user)
        self.assertEqual(db.execute.await_count, 2)

    def test_revoked_session_bound_access_token_is_rejected(self):
        user_id = uuid.uuid4()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=ScalarResult(None))
        request = SimpleNamespace(headers={})
        token = create_access_token(str(user_id), {"session_jti": "revoked-session"})

        with self.assertRaises(HTTPException) as error:
            asyncio.run(get_current_user(request, db, token))

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(db.execute.await_count, 1)

    def test_legacy_access_token_without_session_binding_is_rejected(self):
        user_id = uuid.uuid4()
        db = AsyncMock()
        request = SimpleNamespace(headers={})
        token = create_access_token(str(user_id))

        with self.assertRaises(HTTPException) as error:
            asyncio.run(get_current_user(request, db, token))

        self.assertEqual(error.exception.status_code, 401)
        db.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
