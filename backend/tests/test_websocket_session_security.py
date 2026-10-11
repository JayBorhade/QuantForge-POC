"""WebSocket authentication and session-revocation regression tests."""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from app.api.routes.websocket import ConnectionManager, _session_is_active


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class SessionContext:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class WebSocketSessionSecurityTests(unittest.TestCase):
    def test_disconnect_user_closes_all_active_connections(self):
        manager = ConnectionManager()
        user_id = str(uuid.uuid4())
        first = type("Socket", (), {"close": AsyncMock()})()
        second = type("Socket", (), {"close": AsyncMock()})()
        manager.active_connections[user_id] = {first, second}

        asyncio.run(manager.disconnect_user(user_id))

        first.close.assert_awaited_once_with(code=4001, reason="Session revoked")
        second.close.assert_awaited_once_with(code=4001, reason="Session revoked")
        self.assertNotIn(user_id, manager.active_connections)

    def test_session_check_accepts_active_session(self):
        user_id = str(uuid.uuid4())
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(object()))
        with patch("app.api.routes.websocket.AsyncSessionLocal", return_value=SessionContext(db)):
            active = asyncio.run(_session_is_active(user_id, "session-1"))
        self.assertTrue(active)
        db.execute.assert_awaited_once()

    def test_session_check_rejects_revoked_or_missing_session(self):
        user_id = str(uuid.uuid4())
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(None))
        with patch("app.api.routes.websocket.AsyncSessionLocal", return_value=SessionContext(db)):
            active = asyncio.run(_session_is_active(user_id, "revoked-session"))
        self.assertFalse(active)

    def test_session_check_rejects_invalid_user_id(self):
        with patch("app.api.routes.websocket.AsyncSessionLocal") as session_factory:
            active = asyncio.run(_session_is_active("not-a-uuid", "session-1"))
        self.assertFalse(active)
        session_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
