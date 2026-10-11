"""WebSocket authentication and session-revocation regression tests."""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from app.api.routes.websocket import ConnectionManager, _session_is_active, websocket_endpoint


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

    def test_websocket_rejects_missing_origin(self):
        websocket = SimpleNamespace(headers={}, cookies={}, close=AsyncMock())
        asyncio.run(websocket_endpoint(websocket))
        websocket.close.assert_awaited_once_with(code=4403, reason="Origin not allowed")

    def test_websocket_requires_access_cookie_even_if_query_token_could_exist(self):
        websocket = SimpleNamespace(
            headers={"origin": "https://app.quantforge.example"},
            cookies={},
            close=AsyncMock(),
        )
        with patch("app.api.routes.websocket.settings", SimpleNamespace(cors_origins=["https://app.quantforge.example"])):
            asyncio.run(websocket_endpoint(websocket))
        websocket.close.assert_awaited_once_with(code=4001, reason="Authentication required")

    def test_connection_manager_rejects_connections_over_per_user_limit(self):
        async def scenario():
            manager = ConnectionManager()
            user_id = str(uuid.uuid4())
            sockets = [
                type("Socket", (), {"accept": AsyncMock(), "close": AsyncMock()})()
                for _ in range(manager.MAX_CONNECTIONS_PER_USER + 1)
            ]
            for socket in sockets[:-1]:
                self.assertTrue(await manager.connect(user_id, socket))
            self.assertFalse(await manager.connect(user_id, sockets[-1]))
            sockets[-1].accept.assert_not_awaited()
            sockets[-1].close.assert_awaited_once_with(code=4008, reason="Connection limit reached")
            self.assertEqual(len(manager.active_connections[user_id]), manager.MAX_CONNECTIONS_PER_USER)
        asyncio.run(scenario())

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
        db.execute = AsyncMock(side_effect=[Result(object()), Result(object())])
        with patch("app.api.routes.websocket.AsyncSessionLocal", return_value=SessionContext(db)):
            active = asyncio.run(_session_is_active(user_id, "session-1"))
        self.assertTrue(active)
        self.assertEqual(db.execute.await_count, 2)

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
