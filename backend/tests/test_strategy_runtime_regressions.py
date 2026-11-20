"""Regression tests for provider date normalization and RSI exit safety."""

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from strategies.backtest import BacktestEngine
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy


class BacktestDateContractTests(unittest.TestCase):
    def test_yfinance_reset_index_date_is_normalized(self):
        index = pd.DatetimeIndex(["2026-01-02", "2026-01-05"], name="Date")
        frame = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000, 1100],
            },
            index=index,
        )
        ticker = MagicMock()
        ticker.history.return_value = frame
        with patch("strategies.backtest.yf.Ticker", return_value=ticker):
            normalized = BacktestEngine._fetch_historical(
                "AAPL", pd.Timestamp("2026-01-01").to_pydatetime(),
                pd.Timestamp("2026-02-01").to_pydatetime(),
            )

        self.assertIn("date", normalized.columns)
        self.assertNotIn("Date", normalized.columns)
        self.assertEqual(normalized["date"].iloc[0], pd.Timestamp("2026-01-02"))


class RSICooldownExitTests(unittest.TestCase):
    def test_trailing_stop_exit_is_not_suppressed_by_cooldown(self):
        prices = pd.Series([100.0, 100.0, 100.0, 70.0, 69.0])
        rsi_values = pd.Series([50.0, 50.0, 10.0, 10.0, 10.0])
        indicator = MagicMock()
        indicator.rsi.return_value = rsi_values

        with patch("strategies.rsi_mean_reversion.ta.momentum.RSIIndicator", return_value=indicator):
            result = RSIMeanReversionStrategy(
                "AAPL",
                {"rsi_period": 2, "cooldown_bars": 5, "trailing_stop_pct": 0.1},
            ).generate_signals(pd.DataFrame({"close": prices}))

        self.assertEqual(result.iloc[2]["signal"], "buy")
        self.assertEqual(result.iloc[3]["signal"], "sell")


if __name__ == "__main__":
    unittest.main()
