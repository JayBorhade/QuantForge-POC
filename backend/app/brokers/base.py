"""Provider-neutral broker contract.

Concrete adapters must never blindly retry an uncertain submission. If a provider supports
client-side idempotency, adapters must forward client_order_id to that provider.
Otherwise the execution/reconciliation layer must treat submission timeouts as uncertain
and reconcile rather than resubmit.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping, Protocol

from app.models.order import OrderSide, OrderType


@dataclass(frozen=True)
class BrokerOrderRequest:
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None = None
    broker_params: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_id: str
    status: str = "submitted"


class BrokerAdapter(Protocol):
    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult: ...
    async def cancel_order(self, broker_order_id: str) -> None: ...
    async def get_order(self, broker_order_id: str) -> BrokerOrderResult: ...
