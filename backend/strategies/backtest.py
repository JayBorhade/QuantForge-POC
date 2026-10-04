"""Backtesting engine with performance metrics."""

import logging
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import yfinance as yf

from strategies.base import BacktestResult
from strategies.registry import get_strategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Runs historical backtests and computes metrics."""

    def run(
        self,
        strategy_id: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
        strategy_type: str = "ema_crossover",
        symbol: str = "AAPL",
        parameters: dict = None,
    ) -> Dict[str, Any]:
        parameters = parameters or {}
        df = self._fetch_historical(symbol, start_date, end_date)
        if df.empty:
            return {"error": "No data available for backtest period"}

        strategy = get_strategy(strategy_type, symbol, parameters, mode="backtest")
        signals_df = strategy.generate_signals(df)
        result = self._simulate_trades(signals_df, initial_capital)
        return {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_capital": initial_capital,
            **result,
        }

    def _fetch_historical(
        self, symbol: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        df.columns = [c.lower() for c in df.columns]
        return df.reset_index()

    def _simulate_trades(self, df: pd.DataFrame, initial_capital: float) -> Dict[str, Any]:
        capital = initial_capital
        position = 0
        entry_price = 0.0
        trades: List[Dict] = []
        equity_curve: List[Dict] = []

        for i, row in df.iterrows():
            price = row["close"]
            signal = row.get("signal", "hold")

            if signal == "buy" and position == 0:
                position = capital * 0.1 / price
                entry_price = price
                capital -= position * price
            elif signal == "sell" and position > 0:
                pnl = (price - entry_price) * position
                capital += position * price
                trades.append({
                    "entry": entry_price,
                    "exit": price,
                    "pnl": round(pnl, 2),
                    "return_pct": round((price - entry_price) / entry_price * 100, 2),
                })
                position = 0

            portfolio_value = capital + position * price
            equity_curve.append({"index": i, "value": round(portfolio_value, 2)})

        final_value = capital + position * df.iloc[-1]["close"]
        total_return = (final_value - initial_capital) / initial_capital

        returns = pd.Series([t["return_pct"] / 100 for t in trades])
        sharpe = self._sharpe_ratio(returns) if len(returns) > 1 else 0.0
        max_dd = self._max_drawdown([e["value"] for e in equity_curve])
        wins = sum(1 for t in trades if t["pnl"] > 0)
        win_rate = wins / len(trades) if trades else 0.0

        return {
            "total_return": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd * 100, 2),
            "win_rate": round(win_rate * 100, 2),
            "total_trades": len(trades),
            "final_capital": round(final_value, 2),
            "equity_curve": equity_curve[-100:],
            "trade_history": trades,
        }

    @staticmethod
    def _sharpe_ratio(returns: pd.Series, risk_free: float = 0.02) -> float:
        if returns.std() == 0:
            return 0.0
        excess = returns.mean() - risk_free / 252
        return float(excess / returns.std() * np.sqrt(252))

    @staticmethod
    def _max_drawdown(equity: List[float]) -> float:
        if not equity:
            return 0.0
        peak = equity[0]
        max_dd = 0.0
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        return max_dd
