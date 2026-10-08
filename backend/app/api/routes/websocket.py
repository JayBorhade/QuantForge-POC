"""WebSocket routes for live updates."""

import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt

from app.core.config import get_settings

router = APIRouter(tags=["WebSocket"])
settings = get_settings()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

    async def send_personal(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id].copy():
                try:
                    await connection.send_json(message)
                except Exception:
                    self.active_connections[user_id].discard(connection)


manager = ConnectionManager()


def init_websocket_manager():
    from app.services.websocket_broadcast import set_manager
    set_manager(manager)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    """Authenticated control channel for user updates and market-data subscriptions."""
    if not token:
        await websocket.close(code=4001)
        return

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access" or not payload.get("sub"):
            await websocket.close(code=4001)
            return
        user_id = str(payload["sub"])
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)
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
