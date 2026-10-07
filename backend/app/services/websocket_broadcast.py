"""Bridge for broadcasting WebSocket messages from sync/async code."""

from typing import Any, Dict

_manager = None


def set_manager(manager) -> None:
    global _manager
    _manager = manager


async def broadcast_to_user(user_id: str, message: Dict[str, Any]) -> None:
    if _manager:
        await _manager.send_personal(str(user_id), message)


async def broadcast_trade_alert(user_id: str, trade_data: Dict[str, Any]) -> None:
    await broadcast_to_user(
        user_id,
        {"type": "trade", "data": trade_data},
    )


async def broadcast_notification(user_id: str, title: str, message: str) -> None:
    await broadcast_to_user(
        user_id,
        {"type": "notification", "title": title, "message": message},
    )
