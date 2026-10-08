"""Compatibility facade for the canonical Angel One adapter."""

from typing import Any, Dict, List

from app.brokers.angel_one import AngelOneBrokerAdapter
from app.brokers.base import BrokerOrderRequest
from app.models.order import OrderSide, OrderType
from brokers.base import BaseBrokerAdapter, OrderRequest, OrderResponse


class AngelOneAdapter(AngelOneBrokerAdapter, BaseBrokerAdapter):
    """Legacy API facade; execution is delegated to app.brokers.angel_one."""

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        from decimal import Decimal

        broker_params = getattr(order, "broker_params", {})
        result = await self.submit_order(
            BrokerOrderRequest(
                client_order_id=f"legacy-{order.symbol}-{order.side}-{order.quantity}",
                symbol=order.symbol,
                side=OrderSide(order.side.lower()),
                order_type=OrderType(order.order_type.lower()),
                quantity=Decimal(str(order.quantity)),
                limit_price=Decimal(str(order.price)) if order.price is not None else None,
                broker_params=broker_params,
            )
        )
        return OrderResponse(result.broker_order_id, result.status, 0.0, None, {})

    async def cancel_order(self, order_id: str) -> bool:
        await super().cancel_order(order_id)
        return True

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        raise ValueError("Angel One quote requires exchange and symboltoken")

    async def get_positions(self) -> List[Dict[str, Any]]:
        return await super().get_positions()
