"""VWAP Intraday Strategy."""

from typing import Any, Dict

import numpy as np
import pandas as pd

from strategies.base import BaseStrategy, Signal


class VWAPIntradayStrategy(BaseStrategy):
    """VWAP crossover with session handling, volume filters, and volatility checks."""

    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            "volume_multiplier": 1.5,
            "volatility_threshold": 0.02,
            "session_start": "09:30",
            "session_end": "16:00",
            "position_size_pct": 0.08,
        }

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
        cumulative_vol = df["volume"].cumsum()
        return cumulative_tp_vol / cumulative_vol.replace(0, np.nan)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        params = {**self.get_default_parameters(), **self.parameters}
        vol_mult = params["volume_multiplier"]
        vol_threshold = params["volatility_threshold"]

        df = df.copy()
        df["vwap"] = self._calculate_vwap(df)
        df["returns"] = df["close"].pct_change()
        df["volatility"] = df["returns"].rolling(20).std()
        df["avg_volume"] = df["volume"].rolling(20).mean()
        df["signal"] = Signal.HOLD.value

        df["above_vwap"] = df["close"] > df["vwap"]
        df["vwap_cross_up"] = df["above_vwap"] & ~df["above_vwap"].shift(1).fillna(False)
        df["vwap_cross_down"] = ~df["above_vwap"] & df["above_vwap"].shift(1).fillna(False)

        high_volume = df["volume"] > df["avg_volume"] * vol_mult
        low_volatility = df["volatility"] < vol_threshold

        buy_mask = df["vwap_cross_up"] & high_volume & low_volatility
        sell_mask = df["vwap_cross_down"] & high_volume

        df.loc[buy_mask, "signal"] = Signal.BUY.value
        df.loc[sell_mask, "signal"] = Signal.SELL.value

        return df
