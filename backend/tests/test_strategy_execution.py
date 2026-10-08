"""Deterministic strategy execution intent tests."""

import unittest
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.strategy_execution import StrategyExecutionError, build_execution_intent
from strategies.base import Signal


def make_strategy(**parameters):
    return SimpleNamespace(id=uuid4(), symbol="AAPL", parameters=parameters)


def make_portfolio(cash="10000", positions=()):
    return SimpleNamespace(cash_balance=Decimal(cash), positions=list(positions))


class StrategyExecutionIntentTests(unittest.TestCase):
    def test_buy_uses_configured_cash_allocation(self):
        strategy = make_strategy(position_size_pct="0.25")
        intent = build_execution_intent(
            strategy=strategy,
            portfolio=make_portfolio(cash="10000"),
            signal=Signal.BUY,
            price=Decimal("100"),
            signal_at="2026-10-08T10:00:00+00:00",
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent.quantity, Decimal("25"))
        self.assertEqual(intent.symbol, "AAPL")

    def test_sell_closes_current_position(self):
        position = SimpleNamespace(symbol="AAPL", quantity=Decimal("7"))
        intent = build_execution_intent(
            strategy=make_strategy(position_size_pct="0.10"),
            portfolio=make_portfolio(cash="0", positions=[position]),
            signal=Signal.SELL,
            price=Decimal("100"),
            signal_at="2026-10-08T10:00:00+00:00",
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent.quantity, Decimal("7"))

    def test_hold_signal_is_noop(self):
        intent = build_execution_intent(
            strategy=make_strategy(),
            portfolio=make_portfolio(),
            signal=Signal.HOLD,
            price=Decimal("100"),
            signal_at="2026-10-08T10:00:00+00:00",
        )
        self.assertIsNone(intent)

    def test_sell_without_position_is_noop(self):
        intent = build_execution_intent(
            strategy=make_strategy(),
            portfolio=make_portfolio(),
            signal=Signal.SELL,
            price=Decimal("100"),
            signal_at="2026-10-08T10:00:00+00:00",
        )
        self.assertIsNone(intent)

    def test_invalid_position_size_is_rejected(self):
        with self.assertRaisesRegex(StrategyExecutionError, "position_size_pct"):
            build_execution_intent(
                strategy=make_strategy(position_size_pct="1.1"),
                portfolio=make_portfolio(),
                signal=Signal.BUY,
                price=Decimal("100"),
                signal_at="2026-10-08T10:00:00+00:00",
            )

    def test_invalid_price_is_rejected(self):
        with self.assertRaisesRegex(StrategyExecutionError, "price must be positive"):
            build_execution_intent(
                strategy=make_strategy(),
                portfolio=make_portfolio(),
                signal=Signal.BUY,
                price=Decimal("0"),
                signal_at="2026-10-08T10:00:00+00:00",
            )

    def test_client_order_id_is_deterministic(self):
        strategy = make_strategy(position_size_pct="0.10")
        kwargs = {
            "strategy": strategy,
            "portfolio": make_portfolio(),
            "signal": Signal.BUY,
            "price": Decimal("100"),
            "signal_at": "2026-10-08T10:00:00+00:00",
        }
        first = build_execution_intent(**kwargs)
        second = build_execution_intent(**kwargs)
        self.assertEqual(first.client_order_id, second.client_order_id)


if __name__ == "__main__":
    unittest.main()
