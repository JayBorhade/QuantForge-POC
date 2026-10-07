"""Provider-neutral broker contract.

Concrete broker integrations must implement this interface. Broker adapters MUST treat
`client_order_id` as an idempotency key so recovery can safely retry an uncertain
submission without creating duplicate orders. The execution
layer never imports provider SDKs directly, which keeps paper trading and
live trading boundaries explicit and testable.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.models.order import OrderSide, OrderType


@dataclass(frozen=True)
class BrokerOrderRequest:
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None = None


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_id: str
    status: str = "submitted"


class BrokerAdapter(Protocol):
    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult: ...
    async def cancel_order(self, broker_order_id: str) -> None: ...
    async def get_order(self, broker_order_id: str) -> BrokerOrderResult: ...
