"""Unit tests for the deterministic paper broker."""

from decimal import Decimal

import pytest

from app.brokers.base import BrokerOrderRequest
from app.brokers.paper_adapter import PaperBrokerAdapter
from app.models.order import OrderSide, OrderType


def request(client_order_id: str = "client-1") -> BrokerOrderRequest:
    return BrokerOrderRequest(
        client_order_id=client_order_id,
        symbol="RELIANCE",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("2"),
    )


@pytest.mark.asyncio
async def test_submit_is_deterministic_and_idempotent() -> None:
    broker = PaperBrokerAdapter()

    first = await broker.submit_order(request())
    second = await broker.submit_order(request())

    assert first == second
    assert first.broker_order_id == "paper-client-1"
    assert first.status == "submitted"


@pytest.mark.asyncio
async def test_cancel_and_lookup() -> None:
    broker = PaperBrokerAdapter()
    submitted = await broker.submit_order(request())

    await broker.cancel_order(submitted.broker_order_id)
    result = await broker.get_order(submitted.broker_order_id)

    assert result.status == "cancelled"


@pytest.mark.asyncio
async def test_unknown_order_raises() -> None:
    broker = PaperBrokerAdapter()

    with pytest.raises(KeyError):
        await broker.get_order("paper-missing")


@pytest.mark.asyncio
async def test_non_positive_quantity_rejected() -> None:
    broker = PaperBrokerAdapter()

    with pytest.raises(ValueError):
        await broker.submit_order(
            BrokerOrderRequest(
                client_order_id="bad",
                symbol="RELIANCE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0"),
            )
        )
