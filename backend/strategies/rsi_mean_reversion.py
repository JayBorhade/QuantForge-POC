"""RSI Mean Reversion Strategy."""

from typing import Any, Dict

import pandas as pd
import ta

from strategies.base import BaseStrategy, Signal


class RSIMeanReversionStrategy(BaseStrategy):
    """
    Buy when RSI is oversold, sell when overbought.
    Includes trailing stop loss and cooldown timer.
    """

    def get_default_parameters(self) -> Dict[str, Any]:
        return {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "trailing_stop_pct": 0.015,
            "cooldown_bars": 5,
            "position_size_pct": 0.1,
        }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        params = {**self.get_default_parameters(), **self.parameters}
        period = params["rsi_period"]
        oversold = params["oversold"]
        overbought = params["overbought"]
        cooldown = params["cooldown_bars"]
        trail_pct = params["trailing_stop_pct"]

        df = df.copy()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=period).rsi()
        df["signal"] = Signal.HOLD.value
        df["last_signal_bar"] = -1
        df["stop_loss"] = pd.NA

        position = 0
        trailing_stop = None
        last_signal_idx = -cooldown

        for i in range(period, len(df)):
            if i - last_signal_idx < cooldown:
                continue

            rsi = df.iloc[i]["rsi"]
            price = df.iloc[i]["close"]

            if position == 0 and rsi < oversold:
                df.iloc[i, df.columns.get_loc("signal")] = Signal.BUY.value
                position = 1
                trailing_stop = price * (1 - trail_pct)
                df.loc[df.index[i], "stop_loss"] = trailing_stop
                last_signal_idx = i
            elif position == 1:
                trailing_stop = max(trailing_stop, price * (1 - trail_pct))
                df.loc[df.index[i], "stop_loss"] = trailing_stop
                if rsi > overbought or price < trailing_stop:
                    df.iloc[i, df.columns.get_loc("signal")] = Signal.SELL.value
                    position = 0
                    trailing_stop = None
                    last_signal_idx = i

        df["trailing_stop"] = df["stop_loss"]
        return df
