"""Deterministic tests for strategy-to-order intent translation."""

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
    def test_buy_signal_creates_deterministic_intent(self):
        strategy = make_strategy(position_size_pct="0.10")
        portfolio = make_portfolio()
        first = build_execution_intent(strategy=strategy, portfolio=portfolio, signal=Signal.BUY, price=Decimal("100"), signal_at="2026-10-08T10:00:00+00:00")
        second = build_execution_intent(strategy=strategy, portfolio=portfolio, signal=Signal.BUY, price=Decimal("100"), signal_at="2026-10-08T10:00:00+00:00")
        self.assertIsNotNone(first)
        self.assertEqual(first.quantity, Decimal("10"))
        self.assertEqual(first.client_order_id, second.client_order_id)

    def test_hold_signal_is_noop(self):
        intent = build_execution_intent(strategy=make_strategy(), portfolio=make_portfolio(), signal=Signal.HOLD, price=Decimal("100"), signal_at="2026-10-08T10:00:00+00:00")
        self.assertIsNone(intent)

    def test_sell_without_position_is_noop(self):
        intent = build_execution_intent(strategy=make_strategy(), portfolio=make_portfolio(), signal=Signal.SELL, price=Decimal("100"), signal_at="2026-10-08T10:00:00+00:00")
        self.assertIsNone(intent)

    def test_sell_is_capped_by_existing_position(self):
        position = SimpleNamespace(symbol="AAPL", quantity=Decimal("7"))
        intent = build_execution_intent(strategy=make_strategy(position_size_pct="0.10"), portfolio=make_portfolio(positions=[position]), signal=Signal.SELL, price=Decimal("100"), signal_at="2026-10-08T10:00:00+00:00")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.quantity, Decimal("7"))

    def test_invalid_prices_are_rejected(self):
        for price in ("0", "-1"):
            with self.subTest(price=price):
                with self.assertRaisesRegex(StrategyExecutionError, "price must be positive"):
                    build_execution_intent(strategy=make_strategy(), portfolio=make_portfolio(), signal=Signal.BUY, price=price, signal_at="2026-10-08T10:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
