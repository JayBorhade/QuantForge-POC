import pandas as pd

def rsi_signals(
    df: pd.DataFrame,
    period: int = 14,
    oversold: float = 30,
    overbought: float = 70,
) -> pd.DataFrame:
    """Add RSI and mean-reversion signals to an OHLCV dataframe."""
    data = df.copy()
    delta = data["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    data["rsi"] = 100 - (100 / (1 + rs))

    data["signal"] = 0
    data.loc[data["rsi"] < oversold, "signal"] = 1
    data.loc[data["rsi"] > overbought, "signal"] = -1
    return data
