"""Strategy execution engine."""

import logging
from typing import Any, Dict

import yfinance as yf

from strategies.registry import get_strategy

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Runs strategies in live or paper mode."""

    async def run(self, strategy_id: str, mode: str = "paper") -> Dict[str, Any]:
        # In production, load strategy from DB via async session
        logger.info("Executing strategy %s in %s mode", strategy_id, mode)
        return {
            "strategy_id": strategy_id,
            "mode": mode,
            "status": "completed",
            "signals_generated": 0,
        }

    def fetch_data(self, symbol: str, period: str = "3mo", interval: str = "1d"):
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        if "date" not in df.columns and "datetime" in df.columns:
            df.rename(columns={"datetime": "date"}, inplace=True)
        return df

    def execute_strategy(
        self,
        strategy_type: str,
        symbol: str,
        parameters: dict,
        mode: str = "paper",
    ) -> Dict[str, Any]:
        df = self.fetch_data(symbol)
        strategy = get_strategy(strategy_type, symbol, parameters, mode)
        signals_df = strategy.generate_signals(df)
        trades = signals_df[signals_df["signal"].isin(["buy", "sell"])]
        return {
            "symbol": symbol,
            "mode": mode,
            "total_signals": len(trades),
            "last_signal": trades.iloc[-1]["signal"] if len(trades) > 0 else "hold",
            "last_price": float(signals_df.iloc[-1]["close"]),
        }
