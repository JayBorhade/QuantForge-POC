"""Deterministic in-memory paper broker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.brokers.base import BrokerOrderRequest, BrokerOrderResult


@dataclass
class _PaperOrder:
    request: BrokerOrderRequest
    result: BrokerOrderResult


class PaperBrokerAdapter:
    """Paper broker with deterministic submission and no network I/O."""

    def __init__(self) -> None:
        self._orders: dict[str, _PaperOrder] = {}

    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        if request.quantity <= Decimal("0"):
            raise ValueError("Order quantity must be positive")

        existing = self._orders.get(request.client_order_id)
        if existing is not None:
            return existing.result

        result = BrokerOrderResult(
            broker_order_id=f"paper-{request.client_order_id}",
            status="submitted",
        )
        self._orders[request.client_order_id] = _PaperOrder(request, result)
        return result

    async def cancel_order(self, broker_order_id: str) -> None:
        for client_order_id, stored in self._orders.items():
            if stored.result.broker_order_id == broker_order_id:
                self._orders[client_order_id] = _PaperOrder(
                    stored.request,
                    BrokerOrderResult(broker_order_id, "cancelled"),
                )
                return
        raise KeyError(broker_order_id)

    async def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        for stored in self._orders.values():
            if stored.result.broker_order_id == broker_order_id:
                return stored.result
        raise KeyError(broker_order_id)
