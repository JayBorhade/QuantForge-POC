"""Regression tests for the complete portfolio performance report."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.backtesting.performance_report import (
    benchmark_comparison,
    build_performance_report,
    period_returns,
)
from app.backtesting.types import BacktestTrade


class PortfolioPerformanceReportTests(unittest.TestCase):
    def setUp(self):
        self.equity = [
            {"timestamp": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(), "value": "100000"},
            {"timestamp": datetime(2025, 1, 2, tzinfo=timezone.utc).isoformat(), "value": "110000"},
            {"timestamp": datetime(2025, 2, 1, tzinfo=timezone.utc).isoformat(), "value": "105000"},
            {"timestamp": datetime(2026, 1, 2, tzinfo=timezone.utc).isoformat(), "value": "120000"},
        ]
        self.trades = [
            BacktestTrade(
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                Decimal("100"), Decimal("110"), Decimal("100"),
                Decimal("1000"), Decimal("10"), "signal",
            )
        ]

    def test_monthly_and_yearly_returns(self):
        months = period_returns(self.equity, "month")
        years = period_returns(self.equity, "year")
        self.assertEqual([item["period"] for item in months], ["2025-01", "2025-02", "2026-01"])
        self.assertEqual([item["period"] for item in years], ["2025", "2026"])
        self.assertAlmostEqual(months[0]["return_pct"], 5.0)

    def test_benchmark_excess_return(self):
        benchmark = [
            {"timestamp": self.equity[0]["timestamp"], "value": "100000", "symbol": "NIFTY50"},
            {"timestamp": self.equity[-1]["timestamp"], "value": "110000", "symbol": "NIFTY50"},
        ]
        result = benchmark_comparison(self.equity, benchmark)
        self.assertTrue(result["available"])
        self.assertEqual(result["benchmark_symbol"], "NIFTY50")
        self.assertGreater(result["excess_return_pct"], 0)

    def test_report_is_complete_and_deterministic(self):
        benchmark = [
            {"timestamp": self.equity[0]["timestamp"], "value": "100000", "symbol": "NIFTY50"},
            {"timestamp": self.equity[-1]["timestamp"], "value": "110000", "symbol": "NIFTY50"},
        ]
        first = build_performance_report(
            initial_capital=Decimal("100000"),
            final_capital=Decimal("120000"),
            equity=self.equity,
            trades=self.trades,
            symbol="AAPL",
            benchmark=benchmark,
        )
        second = build_performance_report(
            initial_capital=Decimal("100000"),
            final_capital=Decimal("120000"),
            equity=self.equity,
            trades=self.trades,
            symbol="AAPL",
            benchmark=benchmark,
        )
        self.assertEqual(first, second)
        for section in ("capital", "risk", "returns", "benchmark", "trading", "concentration"):
            self.assertIn(section, first)
        self.assertEqual(first["concentration"]["max_symbol_concentration_pct"], 100.0)
        self.assertEqual(first["returns"]["yearly"][0]["period"], "2025")

    def test_invalid_period_rejected(self):
        with self.assertRaisesRegex(ValueError, "period"):
            period_returns(self.equity, "quarter")


if __name__ == "__main__":
    unittest.main()
