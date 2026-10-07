"""Unit tests for the deterministic paper broker."""

from decimal import Decimal

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


def test_submit_is_deterministic_and_idempotent() -> None:
    broker = PaperBrokerAdapter()

    import asyncio
    first = asyncio.run(broker.submit_order(request()))
    second = asyncio.run(broker.submit_order(request()))

    assert first == second
    assert first.broker_order_id == "paper-client-1"
    assert first.status == "submitted"


@pytest.mark.asyncio
async def test_cancel_and_lookup() -> None:
    broker = PaperBrokerAdapter()
    import asyncio
    submitted = asyncio.run(broker.submit_order(request()))

    asyncio.run(broker.cancel_order(submitted.broker_order_id))
    result = asyncio.run(broker.get_order(submitted.broker_order_id))

    assert result.status == "cancelled"


@pytest.mark.asyncio
async def test_unknown_order_raises() -> None:
    broker = PaperBrokerAdapter()
    import asyncio
    with __import__("contextlib").suppress(KeyError):
        asyncio.run(broker.get_order("paper-missing"))
        raise AssertionError("expected KeyError")


@pytest.mark.asyncio
async def test_non_positive_quantity_rejected() -> None:
    broker = PaperBrokerAdapter()
    import asyncio
    try:
        asyncio.run(broker.submit_order(
            BrokerOrderRequest(
                client_order_id="bad",
                symbol="RELIANCE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0"),
            )
        ))
    except ValueError:
        return
    raise AssertionError("expected ValueError")
