"""Strict strategy parameter validation regressions."""

import unittest

from strategies.registry import validate_strategy_parameters


class StrategyParameterValidationTests(unittest.TestCase):
    def test_rejects_unknown_parameter(self):
        with self.assertRaisesRegex(ValueError, "Unsupported parameter"):
            validate_strategy_parameters("ema_crossover", {"admin_override": True})

    def test_rejects_non_finite_parameter(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            validate_strategy_parameters("ema_crossover", {"position_size_pct": float("nan")})

    def test_rejects_invalid_ema_order(self):
        with self.assertRaisesRegex(ValueError, "fast_ema"):
            validate_strategy_parameters("ema_crossover", {"fast_ema": 50, "slow_ema": 20})

    def test_accepts_documented_backtest_parameters(self):
        values = validate_strategy_parameters(
            "ema_crossover",
            {"transaction_cost_pct": 0.001, "slippage_pct": 0.0005, "benchmark_symbol": "SPY"},
        )
        self.assertEqual(values["benchmark_symbol"], "SPY")

    def test_rejects_malformed_session_time(self):
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            validate_strategy_parameters("vwap_intraday", {"session_start": "25:99"})


if __name__ == "__main__":
    unittest.main()
