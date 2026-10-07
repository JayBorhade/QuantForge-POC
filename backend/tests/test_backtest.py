"""Deterministic unit tests for the backtest simulation core.

Run from backend/: python -m unittest discover -s tests -v
"""
import unittest

import pandas as pd

from strategies.backtest import BacktestEngine


class BacktestSimulationTests(unittest.TestCase):
    def setUp(self):
        self.engine = BacktestEngine()
        self.engine._strategy_parameters = {
            "position_size_pct": 0.1,
            "transaction_cost_pct": 0.0,
            "slippage_pct": 0.0,
        }

    def frame(self, rows):
        return pd.DataFrame(rows, columns=["open", "high", "low", "close", "signal"])

    def test_equity_curve_starts_with_initial_capital(self):
        df = self.frame([
            (100, 101, 99, 100, "hold"),
            (100, 101, 99, 100, "hold"),
        ])
        result = self.engine._simulate_trades(df, 1000)
        self.assertEqual(result["equity_curve"][0]["index"], -1)
        self.assertEqual(result["equity_curve"][0]["value"], 1000.0)
        self.assertEqual(result["final_capital"], 1000.0)

    def test_buy_signal_fills_on_next_bar_and_liquidates(self):
        df = self.frame([
            (100, 101, 99, 100, "buy"),
            (110, 112, 109, 111, "hold"),
        ])
        result = self.engine._simulate_trades(df, 1000)
        self.assertEqual(result["total_trades"], 1)
        trade = result["trade_history"][0]
        self.assertEqual(trade["entry"], 110.0)
        self.assertEqual(trade["reason"], "end_of_period")
        self.assertGreater(result["final_capital"], 1000.0)
        self.assertEqual(result["equity_curve"][-1]["value"], result["final_capital"])

    def test_invalid_position_size_is_rejected(self):
        self.engine._strategy_parameters["position_size_pct"] = 0
        df = self.frame([(100, 101, 99, 100, "hold")])
        with self.assertRaisesRegex(ValueError, "position_size_pct"):
            self.engine._simulate_trades(df, 1000)

    def test_stop_loss_gap_exits_at_open(self):
        self.engine._strategy_parameters["stop_loss"] = 95
        df = self.frame([
            (100, 101, 99, 100, "buy"),
            (100, 101, 99, 100, "hold"),
            (90, 92, 88, 91, "hold"),
        ])
        df["stop_loss"] = [95, 95, 95]
        result = self.engine._simulate_trades(df, 1000)
        reasons = [trade["reason"] for trade in result["trade_history"]]
        self.assertIn("stop_loss_gap", reasons)


if __name__ == "__main__":
    unittest.main()
