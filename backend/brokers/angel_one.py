"""Angel One SmartAPI adapter."""

import logging
from typing import Any, Dict, List

from brokers.base import BaseBrokerAdapter, OrderRequest, OrderResponse

logger = logging.getLogger(__name__)


class AngelOneAdapter(BaseBrokerAdapter):
    """Angel One SmartAPI integration."""

    BASE_URL = "https://apiconnect.angelone.in"

    async def connect(self) -> bool:
        logger.info("Connecting to Angel One SmartAPI")
        return bool(self.api_key and self.access_token)

    async def get_positions(self) -> List[Dict[str, Any]]:
        return []

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        logger.info("Angel One order: %s %s", order.side, order.symbol)
        return OrderResponse(
            order_id=f"AOL-{order.symbol}",
            status="pending",
            filled_quantity=0,
            average_price=None,
            raw={"broker": "angel_one"},
        )

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        return {"symbol": symbol, "ltp": 0.0, "broker": "angel_one"}
