import pandas as pd

def ema_crossover_signals(
    df: pd.DataFrame,
    fast_period: int = 20,
    slow_period: int = 50,
) -> pd.DataFrame:
    """Add EMA values and crossover signals to an OHLCV dataframe."""
    data = df.copy()
    data["ema_fast"] = data["close"].ewm(span=fast_period, adjust=False).mean()
    data["ema_slow"] = data["close"].ewm(span=slow_period, adjust=False).mean()

    previous_fast = data["ema_fast"].shift(1)
    previous_slow = data["ema_slow"].shift(1)

    data["signal"] = 0
    data.loc[
        (data["ema_fast"] > data["ema_slow"])
        & (previous_fast <= previous_slow),
        "signal",
    ] = 1
    data.loc[
        (data["ema_fast"] < data["ema_slow"])
        & (previous_fast >= previous_slow),
        "signal",
    ] = -1
    return data
