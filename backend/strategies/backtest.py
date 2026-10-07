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
        self._strategy_parameters = parameters\n        result = self._simulate_trades(signals_df, initial_capital)
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
        """Simulate long-only trades with sizing, costs, slippage and stop losses.

        Signals are acted on at the current bar close. Stop losses, when supplied
        by a strategy, are evaluated against the bar's low before a normal sell
        signal. This keeps the engine deterministic and avoids inventing fills.
        """
        capital = float(initial_capital)
        position = 0.0
        entry_price = 0.0
        entry_cost = 0.0
        stop_loss = None
        take_profit = None
        trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []

        position_size_pct = float(self._strategy_parameters.get("position_size_pct", 0.10))
        position_size_pct = min(max(position_size_pct, 0.0), 1.0)
        transaction_cost_pct = float(self._strategy_parameters.get("transaction_cost_pct", 0.001))
        slippage_pct = float(self._strategy_parameters.get("slippage_pct", 0.0005))

        for i, row in df.iterrows():
            price = float(row["close"])
            signal = row.get("signal", "hold")
            if pd.isna(price) or price <= 0:
                continue

            row_stop = row.get("stop_loss")
            row_take_profit = row.get("take_profit")

            exit_price = None
            exit_reason = None

            if position > 0:
                low = float(row["low"]) if not pd.isna(row.get("low")) else price
                high = float(row["high"]) if not pd.isna(row.get("high")) else price
                if stop_loss is not None and low <= stop_loss:
                    exit_price = stop_loss * (1.0 - slippage_pct)
                    exit_reason = "stop_loss"
                elif take_profit is not None and high >= take_profit:
                    exit_price = take_profit * (1.0 - slippage_pct)
                    exit_reason = "take_profit"
                elif signal == "sell":
                    exit_price = price * (1.0 - slippage_pct)
                    exit_reason = "signal"

            if position > 0 and exit_price is not None:
                gross = position * exit_price
                exit_fee = gross * transaction_cost_pct
                capital += gross - exit_fee
                pnl = (exit_price - entry_price) * position - entry_cost - exit_fee
                trades.append({
                    "entry": round(entry_price, 6),
                    "exit": round(exit_price, 6),
                    "quantity": round(position, 6),
                    "pnl": round(pnl, 2),
                    "return_pct": round((exit_price - entry_price) / entry_price * 100, 4),
                    "reason": exit_reason,
                })
                position = 0.0
                entry_price = 0.0
                entry_cost = 0.0
                stop_loss = None
                take_profit = None

            if signal == "buy" and position == 0:
                fill_price = price * (1.0 + slippage_pct)
                allocation = capital * position_size_pct
                quantity = allocation / (fill_price * (1.0 + transaction_cost_pct))
                cost = quantity * fill_price
                fee = cost * transaction_cost_pct
                if quantity > 0 and cost + fee <= capital:
                    capital -= cost + fee
                    position = quantity
                    entry_price = fill_price
                    entry_cost = fee
                    if row_stop is not None and not pd.isna(row_stop):
                        stop_loss = float(row_stop)
                    if row_take_profit is not None and not pd.isna(row_take_profit):
                        take_profit = float(row_take_profit)

            portfolio_value = capital + position * price
            equity_curve.append({"index": i, "value": round(portfolio_value, 2)})

        if position > 0 and len(df) > 0:
            final_price = float(df.iloc[-1]["close"]) * (1.0 - slippage_pct)
            gross = position * final_price
            exit_fee = gross * transaction_cost_pct
            capital += gross - exit_fee
            pnl = (final_price - entry_price) * position - entry_cost - exit_fee
            trades.append({
                "entry": round(entry_price, 6),
                "exit": round(final_price, 6),
                "quantity": round(position, 6),
                "pnl": round(pnl, 2),
                "return_pct": round((final_price - entry_price) / entry_price * 100, 4),
                "reason": "end_of_period",
            })
            position = 0.0

        final_value = capital
        total_return = (final_value - initial_capital) / initial_capital
        equity_values = [e["value"] for e in equity_curve]
        equity_returns = pd.Series(equity_values).pct_change().dropna()
        sharpe = self._sharpe_ratio(equity_returns) if len(equity_returns) > 1 else 0.0
        max_dd = self._max_drawdown(equity_values)
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
