"""Breakout Strategy with ATR stop loss."""

from typing import Any, Dict

import pandas as pd
import ta

from strategies.base import BaseStrategy, Signal


class BreakoutStrategy(BaseStrategy):
    """Breakout detection with ATR-based stop loss and dynamic risk."""

    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            "lookback": 20,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "confirmation_bars": 2,
            "risk_pct": 0.02,
            "position_size_pct": 0.1,
        }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        params = {**self.get_default_parameters(), **self.parameters}
        lookback = params["lookback"]
        atr_period = params["atr_period"]
        atr_mult = params["atr_multiplier"]
        confirm = params["confirmation_bars"]

        df = df.copy()
        df["high_band"] = df["high"].rolling(lookback).max()
        df["low_band"] = df["low"].rolling(lookback).min()
        df["atr"] = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], window=atr_period
        ).average_true_range()
        df["signal"] = Signal.HOLD.value

        breakout_up = df["close"] > df["high_band"].shift(1)
        breakout_down = df["close"] < df["low_band"].shift(1)

        confirmed_up = breakout_up.rolling(confirm).sum() >= confirm
        confirmed_down = breakout_down.rolling(confirm).sum() >= confirm

        df.loc[confirmed_up, "signal"] = Signal.BUY.value
        df.loc[confirmed_up, "stop_loss"] = df.loc[confirmed_up, "close"] - (
            df.loc[confirmed_up, "atr"] * atr_mult
        )
        df.loc[confirmed_down, "signal"] = Signal.SELL.value
        df.loc[confirmed_down, "stop_loss"] = df.loc[confirmed_down, "close"] + (
            df.loc[confirmed_down, "atr"] * atr_mult
        )

        return df
