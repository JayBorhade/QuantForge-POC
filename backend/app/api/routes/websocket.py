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
    # Live/trading updates are user-scoped; never create an anonymous connection.
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
    try:
        await websocket.send_json({"type": "connected", "message": "QuantForge live feed active"})
        tick = 0
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data) if data else {}
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                tick += 1
                await websocket.send_json({
                    "type": "heartbeat",
                    "tick": tick,
                    "server_time": asyncio.get_event_loop().time(),
                })
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
