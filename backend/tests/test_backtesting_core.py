"""Regression tests for the provider-neutral backtesting core."""

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.backtesting.simulator import BacktestSimulator
from app.backtesting.types import BacktestBar, BacktestConfig


class BacktestingCoreTests(unittest.TestCase):
    def setUp(self):
        self.config = BacktestConfig(
            initial_capital=Decimal("1000"),
            position_size_pct=Decimal("0.10"),
            transaction_cost_pct=Decimal("0"),
            slippage_pct=Decimal("0"),
        )

    def bars(self, rows):
        return [
            BacktestBar(
                datetime(2026, 1, index + 1, tzinfo=timezone.utc),
                *(Decimal(str(value)) for value in row),
            )
            for index, row in enumerate(rows)
        ]

    def test_signal_executes_on_next_open(self):
        result = BacktestSimulator().run(
            self.bars([(100, 101, 99, 100), (110, 112, 109, 111)]),
            [{"signal": "buy"}, {"signal": "hold"}],
            self.config,
        )
        self.assertEqual(result.total_trades, 1)
        self.assertEqual(result.trades[0].entry_price, Decimal("110"))
        self.assertGreater(result.final_capital, Decimal("1000"))

    def test_costs_reduce_returns(self):
        bars = self.bars([(100, 101, 99, 100), (110, 112, 109, 111)])
        free = BacktestSimulator().run(bars, [{"signal": "buy"}, {"signal": "hold"}], self.config)
        costly = BacktestSimulator().run(
            bars,
            [{"signal": "buy"}, {"signal": "hold"}],
            BacktestConfig(
                initial_capital=Decimal("1000"),
                position_size_pct=Decimal("0.10"),
                transaction_cost_pct=Decimal("0.01"),
                slippage_pct=Decimal("0.01"),
            ),
        )
        self.assertGreater(free.final_capital, costly.final_capital)

    def test_stop_loss_gap(self):
        result = BacktestSimulator().run(
            self.bars([(100, 101, 99, 100), (100, 101, 99, 100), (90, 92, 88, 91)]),
            [
                {"signal": "buy", "stop_loss": 95},
                {"signal": "hold", "stop_loss": 95},
                {"signal": "hold", "stop_loss": 95},
            ],
            self.config,
        )
        self.assertEqual(result.trades[0].reason, "stop_loss_gap")

    def test_invalid_ohlc(self):
        with self.assertRaisesRegex(ValueError, "OHLC"):
            BacktestSimulator().run(self.bars([(100, 99, 98, 100)]), [{"signal": "hold"}], self.config)

    def test_mismatched_inputs(self):
        with self.assertRaisesRegex(ValueError, "equal length"):
            BacktestSimulator().run(self.bars([(100, 101, 99, 100)]), [], self.config)

    def test_unsorted_bars_are_rejected(self):
        bars = self.bars([(100, 101, 99, 100), (101, 102, 100, 101)])
        bars.reverse()
        with self.assertRaisesRegex(ValueError, "strictly chronological"):
            BacktestSimulator().run(bars, [{"signal": "hold"}, {"signal": "hold"}], self.config)

    def test_duplicate_bar_timestamps_are_rejected(self):
        bars = self.bars([(100, 101, 99, 100), (101, 102, 100, 101)])
        bars[1] = BacktestBar(bars[0].timestamp, bars[1].open, bars[1].high, bars[1].low, bars[1].close)
        with self.assertRaisesRegex(ValueError, "strictly chronological"):
            BacktestSimulator().run(bars, [{"signal": "hold"}, {"signal": "hold"}], self.config)

    def test_non_finite_prices_are_rejected(self):
        bars = [BacktestBar(datetime(2026, 1, 1, tzinfo=timezone.utc), Decimal("NaN"), Decimal("NaN"), Decimal("NaN"), Decimal("NaN"))]
        with self.assertRaisesRegex(ValueError, "finite"):
            BacktestSimulator().run(bars, [{"signal": "hold"}], self.config)

    def test_non_finite_configuration_is_rejected(self):
        invalid = BacktestConfig(initial_capital=Decimal("NaN"))
        with self.assertRaisesRegex(ValueError, "finite"):
            BacktestSimulator().run(self.bars([(100, 101, 99, 100)]), [{"signal": "hold"}], invalid)

    def test_unknown_signal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported signal"):
            BacktestSimulator().run(self.bars([(100, 101, 99, 100)]), [{"signal": "maybe"}], self.config)

    def test_non_positive_stop_loss_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite positive"):
            BacktestSimulator().run(
                self.bars([(100, 101, 99, 100)]),
                [{"signal": "buy", "stop_loss": -1}],
                self.config,
            )

    def test_nan_optional_stops_from_pandas_are_ignored(self):
        result = BacktestSimulator().run(
            self.bars([(100, 101, 99, 100), (110, 112, 109, 111)]),
            [{"signal": "buy", "stop_loss": 95}, {"signal": "hold", "stop_loss": float("nan")}],
            self.config,
        )
        self.assertEqual(result.total_trades, 1)


if __name__ == "__main__":
    unittest.main()
