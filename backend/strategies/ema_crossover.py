"""EMA Crossover Strategy — 20/50 EMA with stop loss and take profit."""

from typing import Any, Dict

import pandas as pd
import ta

from strategies.base import BaseStrategy, Signal


class EMACrossoverStrategy(BaseStrategy):
    """
    Buy when 20 EMA crosses above 50 EMA.
    Sell when 20 EMA crosses below 50 EMA.
    Includes stop loss, take profit, and position sizing.
    """

    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            "fast_ema": 20,
            "slow_ema": 50,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.04,
            "position_size_pct": 0.1,
            "risk_pct": 0.02,
        }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        params = {**self.get_default_parameters(), **self.parameters}
        fast = params["fast_ema"]
        slow = params["slow_ema"]
        sl_pct = params["stop_loss_pct"]
        tp_pct = params["take_profit_pct"]

        df = df.copy()
        df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=fast).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=slow).ema_indicator()

        df["signal"] = Signal.HOLD.value
        df.loc[df["ema_fast"] > df["ema_slow"], "crossover"] = 1
        df.loc[df["ema_fast"] < df["ema_slow"], "crossover"] = -1
        df["crossover_change"] = df["crossover"].diff()

        buy_mask = df["crossover_change"] == 2
        sell_mask = df["crossover_change"] == -2

        df.loc[buy_mask, "signal"] = Signal.BUY.value
        df.loc[sell_mask, "signal"] = Signal.SELL.value
        df.loc[buy_mask, "stop_loss"] = df.loc[buy_mask, "close"] * (1 - sl_pct)
        df.loc[buy_mask, "take_profit"] = df.loc[buy_mask, "close"] * (1 + tp_pct)
        df.loc[sell_mask, "stop_loss"] = df.loc[sell_mask, "close"] * (1 + sl_pct)
        df.loc[sell_mask, "take_profit"] = df.loc[sell_mask, "close"] * (1 - tp_pct)

        return df
