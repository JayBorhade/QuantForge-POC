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
        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")
        if not np.isfinite(initial_capital) or initial_capital <= 0:
            raise ValueError("initial_capital must be a finite positive number")
        df = self._fetch_historical(symbol, start_date, end_date)
        if df.empty:
            return {"error": "No data available for backtest period"}

        strategy = get_strategy(strategy_type, symbol, parameters, mode="backtest")
        signals_df = strategy.generate_signals(df)
        self._strategy_parameters = parameters
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
        """Simulate long-only trades with sizing, costs, slippage and stop losses.

        A signal is generated from a completed bar and therefore cannot fill on
        that same bar without introducing look-ahead bias. Signals are executed
        at the next bar's open. Protective stops/targets are then evaluated
        against the current bar's range.
        """
        capital = float(initial_capital)
        position = 0.0
        entry_price = 0.0
        entry_cost = 0.0
        stop_loss = None
        take_profit = None
        trades: List[Dict[str, Any]] = []
        # Include starting capital so drawdown is measured from the true
        # portfolio baseline, including losses on the first bar.
        equity_curve: List[Dict[str, Any]] = [{"index": -1, "value": round(capital, 2)}]

        position_size_pct = float(self._strategy_parameters.get("position_size_pct", 0.10))
        transaction_cost_pct = float(self._strategy_parameters.get("transaction_cost_pct", 0.001))
        slippage_pct = float(self._strategy_parameters.get("slippage_pct", 0.0005))
        if not np.isfinite(position_size_pct) or not 0 < position_size_pct <= 1:
            raise ValueError("position_size_pct must be in (0, 1]")
        if not np.isfinite(transaction_cost_pct) or not 0 <= transaction_cost_pct < 1:
            raise ValueError("transaction_cost_pct must be in [0, 1)")
        if not np.isfinite(slippage_pct) or not 0 <= slippage_pct < 1:
            raise ValueError("slippage_pct must be in [0, 1)")

        pending_signal = "hold"
        pending_stop = None
        pending_take_profit = None

        for i, row in df.iterrows():
            price = float(row["close"])
            if pd.isna(price) or price <= 0:
                continue

            open_price = float(row["open"]) if not pd.isna(row.get("open")) else price

            # Execute the previous completed bar's decision at this bar's open.
            if position > 0 and pending_signal == "sell":
                exit_price = open_price * (1.0 - slippage_pct)
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
                    "reason": "signal",
                })
                position = 0.0
                entry_price = 0.0
                entry_cost = 0.0
                stop_loss = None
                take_profit = None

            if pending_signal == "buy" and position == 0:
                fill_price = open_price * (1.0 + slippage_pct)
                allocation = capital * position_size_pct
                quantity = allocation / (fill_price * (1.0 + transaction_cost_pct))
                cost = quantity * fill_price
                fee = cost * transaction_cost_pct
                if quantity > 0 and cost + fee <= capital:
                    capital -= cost + fee
                    position = quantity
                    entry_price = fill_price
                    entry_cost = fee
                    if pending_stop is not None and not pd.isna(pending_stop):
                        stop_loss = float(pending_stop)
                    if pending_take_profit is not None and not pd.isna(pending_take_profit):
                        take_profit = float(pending_take_profit)

            # Protective orders can trigger during the bar after entry.
            exit_price = None
            exit_reason = None
            if position > 0:
                low = float(row["low"]) if not pd.isna(row.get("low")) else price
                high = float(row["high"]) if not pd.isna(row.get("high")) else price
                # If the market opens through a stop, the stop cannot guarantee
                # its trigger price; use the worse opening price to model gap risk.
                if stop_loss is not None and open_price <= stop_loss:
                    exit_price = open_price * (1.0 - slippage_pct)
                    exit_reason = "stop_loss_gap"
                elif take_profit is not None and open_price >= take_profit:
                    # A favorable gap can execute at the available open.
                    exit_price = open_price * (1.0 - slippage_pct)
                    exit_reason = "take_profit_gap"
                elif stop_loss is not None and low <= stop_loss:
                    exit_price = stop_loss * (1.0 - slippage_pct)
                    exit_reason = "stop_loss"
                elif take_profit is not None and high >= take_profit:
                    exit_price = take_profit * (1.0 - slippage_pct)
                    exit_reason = "take_profit"

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

            portfolio_value = capital + position * price
            equity_curve.append({"index": i, "value": round(portfolio_value, 2)})

            # Queue this completed bar's decision for the next bar's open.
            pending_signal = row.get("signal", "hold")
            pending_stop = row.get("stop_loss")
            pending_take_profit = row.get("take_profit")

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
            # Include liquidation costs in the final equity point so reported
            # drawdown and the chart end at the same value as final_capital.
            if equity_curve:
                equity_curve[-1]["value"] = round(capital, 2)

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
