"""WebSocket routes for live updates."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.session import UserSession
from app.models.user import User

router = APIRouter(tags=["WebSocket"])
settings = get_settings()


class ConnectionManager:
    MAX_CONNECTIONS_PER_USER = 5

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> bool:
        connections = self.active_connections.setdefault(user_id, set())
        if len(connections) >= self.MAX_CONNECTIONS_PER_USER:
            if not connections:
                self.active_connections.pop(user_id, None)
            await websocket.close(code=4008, reason="Connection limit reached")
            return False
        await websocket.accept()
        connections.add(websocket)
        return True

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                self.active_connections.pop(user_id, None)

    async def disconnect_user(self, user_id: str) -> None:
        """Close all WebSocket connections for a user after session revocation."""
        connections = self.active_connections.pop(user_id, set())
        for connection in connections:
            try:
                await connection.close(code=4001, reason="Session revoked")
            except Exception:
                # A connection may already be gone; do not block revocation.
                continue

    async def send_personal(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id].copy():
                try:
                    await connection.send_json(message)
                except Exception:
                    self.active_connections[user_id].discard(connection)


manager = ConnectionManager()


async def _session_is_active(user_id: str, session_jti: str) -> bool:
    """Fail-closed check for access tokens bound to a refresh session."""
    try:
        parsed_user_id = uuid.UUID(user_id)
    except (TypeError, ValueError):
        return False

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserSession).where(
                UserSession.user_id == parsed_user_id,
                UserSession.refresh_token_jti == session_jti,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        if result.scalar_one_or_none() is None:
            return False
        user_result = await db.execute(
            select(User).where(
                User.id == parsed_user_id,
                User.is_active == True,
                User.is_banned == False,
            )
        )
        return user_result.scalar_one_or_none() is not None


def init_websocket_manager():
    from app.services.websocket_broadcast import set_manager
    set_manager(manager)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Cookie-authenticated control channel for user updates and market-data subscriptions."""
    origin = websocket.headers.get("origin")
    if not origin or origin.rstrip("/") not in {item.rstrip("/") for item in settings.cors_origins}:
        await websocket.close(code=4403, reason="Origin not allowed")
        return

    # Do not accept bearer tokens in query strings: URLs commonly reach logs,
    # browser history, proxy telemetry, and monitoring systems.
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access" or not payload.get("sub"):
            await websocket.close(code=4001, reason="Invalid token")
            return
        user_id = str(uuid.UUID(str(payload["sub"])))
        session_jti = payload.get("session_jti")
        # WebSocket access must be tied to a revocable server-side session.
        if not isinstance(session_jti, str) or not session_jti:
            await websocket.close(code=4001, reason="Session required")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    try:
        active_session = await _session_is_active(user_id, session_jti)
    except Exception:
        active_session = False
    if not active_session:
        await websocket.close(code=4001, reason="Session revoked or expired")
        return

    if not await manager.connect(user_id, websocket):
        return
    init_websocket_manager()
    market_task = None

    async def stream_market_data(symbols: list[str]):
        from app.market_data.service import MarketDataService

        service = MarketDataService()
        async for quote in service.multiplex(symbols):
            await websocket.send_json(quote.as_dict())

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "QuantForge live feed active",
                "capabilities": {"market_data": True, "max_symbols": 5},
            }
        )
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "code": "invalid_json"})
                continue

            message_type = msg.get("type")
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif message_type == "subscribe_market_data":
                symbols = msg.get("symbols", [])
                if not isinstance(symbols, list):
                    await websocket.send_json(
                        {"type": "error", "code": "symbols_must_be_list"}
                    )
                    continue
                if market_task:
                    market_task.cancel()
                    await asyncio.gather(market_task, return_exceptions=True)
                try:
                    from app.market_data.service import MarketDataService
                    normalized = list(
                        dict.fromkeys(MarketDataService.normalize_symbol(s) for s in symbols)
                    )
                    if not normalized or len(normalized) > MarketDataService.MAX_SYMBOLS_PER_CONNECTION:
                        raise ValueError("Subscribe to 1-5 symbols per connection")
                    market_task = asyncio.create_task(stream_market_data(normalized))
                    await websocket.send_json(
                        {"type": "market_data_subscribed", "symbols": normalized}
                    )
                except ValueError as exc:
                    await websocket.send_json(
                        {"type": "error", "code": "invalid_subscription", "detail": str(exc)}
                    )
            elif message_type == "unsubscribe_market_data":
                if market_task:
                    market_task.cancel()
                    await asyncio.gather(market_task, return_exceptions=True)
                    market_task = None
                await websocket.send_json({"type": "market_data_unsubscribed"})
            else:
                await websocket.send_json(
                    {"type": "error", "code": "unsupported_message_type"}
                )
    except WebSocketDisconnect:
        pass
    finally:
        if market_task:
            market_task.cancel()
            await asyncio.gather(market_task, return_exceptions=True)
        manager.disconnect(user_id, websocket)
