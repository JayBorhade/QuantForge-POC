"""Regression tests for deterministic backtest analytics."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.backtesting.metrics import (
    annualized_return,
    drawdown_periods,
    exposure_statistics,
    risk_analytics,
    trade_statistics,
)
from app.backtesting.types import BacktestTrade


class BacktestAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.equity = [
            {"timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(), "value": "100000"},
            {"timestamp": datetime(2025, 1, 2, tzinfo=timezone.utc).isoformat(), "value": "110000"},
            {"timestamp": datetime(2025, 1, 3, tzinfo=timezone.utc).isoformat(), "value": "99000"},
            {"timestamp": datetime(2025, 1, 4, tzinfo=timezone.utc).isoformat(), "value": "115000"},
        ]
        self.trades = [
            BacktestTrade(
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                Decimal("100"), Decimal("110"), Decimal("100"), Decimal("1000"), Decimal("10"), "signal",
            ),
            BacktestTrade(
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                datetime(2025, 1, 3, tzinfo=timezone.utc),
                Decimal("110"), Decimal("105"), Decimal("100"), Decimal("-500"), Decimal("-4.5"), "signal",
            ),
        ]

    def test_drawdown_period_is_recovered(self):
        periods = drawdown_periods(self.equity)
        self.assertEqual(len(periods), 1)
        self.assertTrue(periods[0]["recovered"])
        self.assertAlmostEqual(periods[0]["drawdown_pct"], 10.0)

    def test_trade_statistics(self):
        stats = trade_statistics(self.trades)
        self.assertEqual(stats["gross_profit"], 1000.0)
        self.assertEqual(stats["gross_loss"], 500.0)
        self.assertEqual(stats["profit_factor"], 2.0)
        self.assertEqual(stats["best_trade_pnl"], 1000.0)
        self.assertEqual(stats["worst_trade_pnl"], -500.0)

    def test_exposure_is_bounded(self):
        stats = exposure_statistics(self.trades, self.equity)
        self.assertGreater(stats["time_in_market_pct"], 0.0)
        self.assertLessEqual(stats["time_in_market_pct"], 100.0)
        self.assertGreater(stats["max_trade_exposure_pct"], 0.0)

    def test_risk_analytics_is_deterministic(self):
        first = risk_analytics(self.equity, self.trades, Decimal("100000"), Decimal("115000"))
        second = risk_analytics(self.equity, self.trades, Decimal("100000"), Decimal("115000"))
        self.assertEqual(first, second)
        self.assertIn("calmar_ratio", first)
        self.assertIn("drawdown_periods", first)
        self.assertIn("exposure", first)

    def test_annualized_return_is_positive(self):
        value = annualized_return(Decimal("100000"), Decimal("115000"), self.equity)
        self.assertGreater(value, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
