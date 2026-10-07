"""Legacy broker compatibility contract.

This module is retained for the existing broker connection API until provider adapters
are migrated to the canonical execution contract in app.brokers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class OrderResponse:
    order_id: str
    status: str
    filled_quantity: float
    average_price: Optional[float]
    raw: Dict[str, Any]


class BaseBrokerAdapter(ABC):
    """Compatibility interface for broker connection providers."""

    def __init__(self, api_key: str, api_secret: str, access_token: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        pass
