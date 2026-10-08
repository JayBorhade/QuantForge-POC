"""Deterministic tests for strategy-to-order intent translation."""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.strategy_execution import StrategyExecutionError, build_execution_intent
from strategies.base import Signal


def make_strategy(**parameters):
    return SimpleNamespace(
        id=uuid4(),
        symbol="AAPL",
        parameters=parameters,
    )


def make_portfolio(cash="10000", positions=()):
    return SimpleNamespace(
        cash_balance=Decimal(cash),
        positions=list(positions),
    )


def test_buy_signal_creates_deterministic_intent():
    strategy = make_strategy(position_size_pct="0.10")
    portfolio = make_portfolio()

    first = build_execution_intent(
        strategy=strategy,
        portfolio=portfolio,
        signal=Signal.BUY,
        price=Decimal("100"),
        signal_at="2026-10-08T10:00:00+00:00",
    )
    second = build_execution_intent(
        strategy=strategy,
        portfolio=portfolio,
        signal=Signal.BUY,
        price=Decimal("100"),
        signal_at="2026-10-08T10:00:00+00:00",
    )

    assert first is not None
    assert first.quantity == Decimal("10")
    assert first.client_order_id == second.client_order_id


def test_hold_signal_is_noop():
    intent = build_execution_intent(
        strategy=make_strategy(),
        portfolio=make_portfolio(),
        signal=Signal.HOLD,
        price=Decimal("100"),
        signal_at="2026-10-08T10:00:00+00:00",
    )
    assert intent is None


def test_sell_without_position_is_noop():
    intent = build_execution_intent(
        strategy=make_strategy(),
        portfolio=make_portfolio(),
        signal=Signal.SELL,
        price=Decimal("100"),
        signal_at="2026-10-08T10:00:00+00:00",
    )
    assert intent is None


def test_sell_is_capped_by_existing_position():
    position = SimpleNamespace(symbol="AAPL", quantity=Decimal("7"))
    intent = build_execution_intent(
        strategy=make_strategy(position_size_pct="0.10"),
        portfolio=make_portfolio(positions=[position]),
        signal=Signal.SELL,
        price=Decimal("100"),
        signal_at="2026-10-08T10:00:00+00:00",
    )
    assert intent is not None
    assert intent.quantity == Decimal("7")


@pytest.mark.parametrize("price", ["0", "-1"])
def test_invalid_price_is_rejected(price):
    with pytest.raises(StrategyExecutionError, match="price must be positive"):
        build_execution_intent(
            strategy=make_strategy(),
            portfolio=make_portfolio(),
            signal=Signal.BUY,
            price=price,
            signal_at="2026-10-08T10:00:00+00:00",
        )
