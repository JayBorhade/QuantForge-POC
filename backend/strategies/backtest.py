"""Compatibility adapter for the production backtesting core.

Historical-data acquisition and strategy signal generation live at this
boundary; simulation and metrics are provider-neutral under app.backtesting.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict
import pandas as pd
import yfinance as yf

from app.backtesting.simulator import BacktestSimulator
from app.backtesting.metrics import risk_analytics
from app.backtesting.performance_report import build_performance_report
from app.backtesting.types import BacktestBar, BacktestConfig
from strategies.registry import get_strategy


class BacktestEngine:
    """Legacy entry point retained while callers migrate to app.backtesting."""

    def run(
        self,
        strategy_id: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
        strategy_type: str = "ema_crossover",
        symbol: str = "AAPL",
        parameters: dict | None = None,
    ) -> Dict[str, Any]:
        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")
        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        frame = self._fetch_historical(symbol, start_date, end_date)
        if frame.empty:
            return {"error": "No data available for backtest period"}

        strategy = get_strategy(strategy_type, symbol, parameters or {}, mode="backtest")
        signals = strategy.generate_signals(frame)
        bars = [
            BacktestBar(
                timestamp=pd.Timestamp(row["date"] if "date" in row else row["Date"]).to_pydatetime(),
                open=Decimal(str(row["open"])), high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])), close=Decimal(str(row["close"])),
            )
            for _, row in frame.iterrows()
        ]
        signal_rows = signals.to_dict("records")
        config = BacktestConfig(
            initial_capital=Decimal(str(initial_capital)),
            position_size_pct=Decimal(str((parameters or {}).get("position_size_pct", "0.10"))),
            transaction_cost_pct=Decimal(str((parameters or {}).get("transaction_cost_pct", "0.001"))),
            slippage_pct=Decimal(str((parameters or {}).get("slippage_pct", "0.0005"))),
        )
        result = BacktestSimulator().run(bars, signal_rows, config)
        analytics = risk_analytics(
            list(result.equity_curve),
            list(result.trades),
            result.initial_capital,
            result.final_capital,
        )
        benchmark_symbol = (parameters or {}).get("benchmark_symbol")
        benchmark = None
        if benchmark_symbol:
            benchmark_frame = self._fetch_historical(str(benchmark_symbol), start_date, end_date)
            if not benchmark_frame.empty:
                benchmark = [
                    {
                        "timestamp": pd.Timestamp(row["date"] if "date" in row else row["Date"]).to_pydatetime().isoformat(),
                        "value": float(row["close"]),
                        "symbol": str(benchmark_symbol).upper(),
                    }
                    for _, row in benchmark_frame.iterrows()
                ]
        performance_report = build_performance_report(
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            equity=list(result.equity_curve),
            trades=list(result.trades),
            symbol=symbol,
            benchmark=benchmark,
        )
        return {
            "strategy_id": strategy_id, "symbol": symbol,
            "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
            "initial_capital": float(result.initial_capital),
            "total_return": round(float(result.total_return_pct), 4),
            "sharpe_ratio": round(float(result.sharpe_ratio), 4),
            "max_drawdown": round(float(result.max_drawdown_pct), 4),
            "win_rate": round(float(result.win_rate_pct), 4),
            "total_trades": result.total_trades,
            "final_capital": round(float(result.final_capital), 4),
            "equity_curve": list(result.equity_curve)[-100:],
            "analytics": analytics,
            "performance_report": performance_report,
            "trade_history": [
                {
                    "entry": float(t.entry_price), "exit": float(t.exit_price),
                    "quantity": float(t.quantity), "pnl": float(t.pnl),
                    "return_pct": float(t.return_pct), "reason": t.reason,
                    "entry_timestamp": t.entry_timestamp.isoformat(),
                    "exit_timestamp": t.exit_timestamp.isoformat(),
                }
                for t in result.trades
            ],
        }

    @staticmethod
    def _fetch_historical(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        frame = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        frame.columns = [str(c).lower() for c in frame.columns]
        return frame.reset_index()
