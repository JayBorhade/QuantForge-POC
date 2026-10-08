"""Deterministic portfolio-level backtest performance reporting."""
from collections import defaultdict
from decimal import Decimal
from typing import Sequence

from app.backtesting.metrics import (
    annualized_return,
    max_drawdown,
    volatility,
    downside_volatility,
    trade_statistics,
)
from app.backtesting.types import BacktestTrade


def _returns(equity: Sequence[dict]) -> list[Decimal]:
    values = [Decimal(str(point["value"])) for point in equity]
    return [
        (values[i] / values[i - 1]) - Decimal("1")
        for i in range(1, len(values))
        if values[i - 1] > 0
    ]


def _period_key(timestamp: str, period: str) -> str:
    value = str(timestamp)[:10]
    if period == "year":
        return value[:4]
    return value[:7]


def period_returns(equity: Sequence[dict], period: str = "month") -> list[dict]:
    if period not in {"month", "year"}:
        raise ValueError("period must be month or year")
    if len(equity) < 2:
        return []

    grouped: dict[str, list[dict]] = defaultdict(list)
    for point in equity:
        grouped[_period_key(point["timestamp"], period)].append(point)

    result = []
    previous = Decimal(str(equity[0]["value"]))
    for key in sorted(grouped):
        points = grouped[key]
        start = previous
        end = Decimal(str(points[-1]["value"]))
        result.append({
            "period": key,
            "start_value": float(start),
            "end_value": float(end),
            "return_pct": float(((end / start) - Decimal("1")) * 100) if start else 0.0,
        })
        previous = end
    return result


def benchmark_comparison(
    equity: Sequence[dict],
    benchmark: Sequence[dict] | None,
) -> dict:
    if not benchmark or len(benchmark) < 2 or len(equity) < 2:
        return {
            "available": False,
            "benchmark_return_pct": None,
            "portfolio_return_pct": float(((Decimal(str(equity[-1]["value"])) / Decimal(str(equity[0]["value"]))) - 1) * 100) if len(equity) > 1 else 0.0,
            "excess_return_pct": None,
            "benchmark_symbol": None,
        }

    benchmark_values = [Decimal(str(point["value"])) for point in benchmark]
    portfolio_values = [Decimal(str(point["value"])) for point in equity]
    portfolio_return = (portfolio_values[-1] / portfolio_values[0]) - Decimal("1")
    benchmark_return = (benchmark_values[-1] / benchmark_values[0]) - Decimal("1")
    return {
        "available": True,
        "benchmark_return_pct": float(benchmark_return * 100),
        "portfolio_return_pct": float(portfolio_return * 100),
        "excess_return_pct": float((portfolio_return - benchmark_return) * 100),
        "benchmark_symbol": benchmark[0].get("symbol"),
    }


def concentration_statistics(
    trades: Sequence[BacktestTrade],
    equity: Sequence[dict],
    symbol: str,
) -> dict:
    if not trades or not equity:
        return {
            "max_symbol_concentration_pct": 0.0,
            "average_symbol_concentration_pct": 0.0,
            "symbols": [],
        }
    # The current deterministic engine is intentionally long-only and single-symbol.
    return {
        "max_symbol_concentration_pct": 100.0,
        "average_symbol_concentration_pct": 100.0,
        "symbols": [symbol.upper()],
    }


def build_performance_report(
    *,
    initial_capital: Decimal,
    final_capital: Decimal,
    equity: Sequence[dict],
    trades: Sequence[BacktestTrade],
    symbol: str,
    benchmark: Sequence[dict] | None = None,
) -> dict:
    values = [Decimal(str(point["value"])) for point in equity]
    returns = _returns(equity)
    report = {
        "version": 1,
        "capital": {
            "initial": float(initial_capital),
            "final": float(final_capital),
            "net_pnl": float(final_capital - initial_capital),
            "total_return_pct": float(((final_capital / initial_capital) - 1) * 100) if initial_capital else 0.0,
        },
        "risk": {
            "annualized_return_pct": float(annualized_return(initial_capital, final_capital, equity) * 100),
            "volatility_pct": float(volatility(values) * 100),
            "downside_volatility_pct": float(downside_volatility(values) * 100),
            "max_drawdown_pct": float(max_drawdown(values) * 100),
        },
        "returns": {
            "monthly": period_returns(equity, "month"),
            "yearly": period_returns(equity, "year"),
        },
        "benchmark": benchmark_comparison(equity, benchmark),
        "trading": {
            "total_trades": len(trades),
            **trade_statistics(trades),
        },
        "concentration": concentration_statistics(trades, equity, symbol),
    }
    if returns:
        report["risk"]["positive_period_pct"] = float(
            sum(1 for value in returns if value > 0) / len(returns) * 100
        )
    else:
        report["risk"]["positive_period_pct"] = 0.0
    return report
