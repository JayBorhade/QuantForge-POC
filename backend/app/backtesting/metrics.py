"""Deterministic performance and risk analytics."""
from decimal import Decimal
from math import sqrt
from statistics import mean, pstdev
from typing import Sequence

from app.backtesting.types import BacktestTrade


def total_return(initial: Decimal, final: Decimal) -> Decimal:
    return (final - initial) / initial if initial else Decimal("0")


def max_drawdown(equity: Sequence[Decimal]) -> Decimal:
    if not equity:
        return Decimal("0")
    peak, result = equity[0], Decimal("0")
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            result = max(result, (peak - value) / peak)
    return result


def sharpe_ratio(equity: Sequence[Decimal], annual_periods: int = 252) -> Decimal:
    if len(equity) < 3:
        return Decimal("0")
    returns = [
        (equity[i] / equity[i - 1]) - Decimal("1")
        for i in range(1, len(equity))
        if equity[i - 1] > 0
    ]
    if len(returns) < 2:
        return Decimal("0")
    values = [float(x) for x in returns]
    deviation = pstdev(values)
    if deviation == 0:
        return Decimal("0")
    return Decimal(str(mean(values) / deviation * sqrt(annual_periods)))


def win_rate(wins: int, total: int) -> Decimal:
    return Decimal(wins) / Decimal(total) if total else Decimal("0")


def _periods_per_year(equity: Sequence[dict]) -> Decimal:
    if len(equity) < 2:
        return Decimal("252")
    from datetime import datetime
    start = datetime.fromisoformat(str(equity[0]["timestamp"]))
    end = datetime.fromisoformat(str(equity[-1]["timestamp"]))
    days = max((end - start).total_seconds() / 86400, 1.0)
    return Decimal(str(max(1.0, 365.25 * (len(equity) - 1) / days)))


def annualized_return(initial: Decimal, final: Decimal, equity: Sequence[dict]) -> Decimal:
    if initial <= 0 or final <= 0 or len(equity) < 2:
        return Decimal("0")
    from datetime import datetime
    start = datetime.fromisoformat(str(equity[0]["timestamp"]))
    end = datetime.fromisoformat(str(equity[-1]["timestamp"]))
    years = Decimal(str(max((end - start).total_seconds() / 31557600, 1 / 365.25)))
    return (final / initial) ** (Decimal("1") / years) - Decimal("1")


def volatility(equity: Sequence[Decimal], annual_periods: int = 252) -> Decimal:
    if len(equity) < 3:
        return Decimal("0")
    returns = [
        float((equity[i] / equity[i - 1]) - Decimal("1"))
        for i in range(1, len(equity))
        if equity[i - 1] > 0
    ]
    if len(returns) < 2:
        return Decimal("0")
    return Decimal(str(pstdev(returns) * sqrt(annual_periods)))


def downside_volatility(equity: Sequence[Decimal], annual_periods: int = 252) -> Decimal:
    if len(equity) < 3:
        return Decimal("0")
    returns = [
        float((equity[i] / equity[i - 1]) - Decimal("1"))
        for i in range(1, len(equity))
        if equity[i - 1] > 0
    ]
    downside = [min(value, 0.0) for value in returns]
    return Decimal(str(pstdev(downside) * sqrt(annual_periods))) if len(downside) > 1 else Decimal("0")


def drawdown_periods(equity: Sequence[dict]) -> list[dict]:
    if not equity:
        return []
    peak = Decimal(str(equity[0]["value"]))
    peak_time = equity[0]["timestamp"]
    active_start = None
    trough = peak
    trough_time = peak_time
    periods = []
    for point in equity:
        value = Decimal(str(point["value"]))
        timestamp = point["timestamp"]
        if value >= peak:
            if active_start is not None:
                periods.append({
                    "start": active_start,
                    "end": timestamp,
                    "recovered": True,
                    "trough": float(trough),
                    "drawdown_pct": float((peak - trough) / peak * 100) if peak else 0.0,
                })
                active_start = None
            peak = value
            peak_time = timestamp
            trough = value
            trough_time = timestamp
        else:
            if active_start is None:
                active_start = peak_time
                trough = value
            if value < trough:
                trough = value
                trough_time = timestamp
    if active_start is not None:
        periods.append({
            "start": active_start,
            "end": equity[-1]["timestamp"],
            "recovered": False,
            "trough": float(trough),
            "drawdown_pct": float((peak - trough) / peak * 100) if peak else 0.0,
        })
    return periods


def trade_statistics(trades: Sequence[BacktestTrade]) -> dict:
    if not trades:
        return {
            "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 0.0,
            "average_trade_pnl": 0.0, "best_trade_pnl": 0.0, "worst_trade_pnl": 0.0,
            "average_win_pnl": 0.0, "average_loss_pnl": 0.0,
        }
    profits = [float(t.pnl) for t in trades if t.pnl > 0]
    losses = [float(t.pnl) for t in trades if t.pnl < 0]
    gross_profit = sum(profits)
    gross_loss = abs(sum(losses))
    return {
        "gross_profit": round(gross_profit, 8),
        "gross_loss": round(gross_loss, 8),
        "profit_factor": round(gross_profit / gross_loss, 8) if gross_loss else (None if gross_profit else 0.0),
        "average_trade_pnl": round(sum(float(t.pnl) for t in trades) / len(trades), 8),
        "best_trade_pnl": round(max(float(t.pnl) for t in trades), 8),
        "worst_trade_pnl": round(min(float(t.pnl) for t in trades), 8),
        "average_win_pnl": round(sum(profits) / len(profits), 8) if profits else 0.0,
        "average_loss_pnl": round(sum(losses) / len(losses), 8) if losses else 0.0,
    }


def exposure_statistics(trades: Sequence[BacktestTrade], equity: Sequence[dict]) -> dict:
    if not trades or len(equity) < 2:
        return {"time_in_market_pct": 0.0, "average_trade_exposure_pct": 0.0, "max_trade_exposure_pct": 0.0}
    total_seconds = max(
        (float(__import__("datetime").datetime.fromisoformat(str(equity[-1]["timestamp"])) .timestamp())
         - float(__import__("datetime").datetime.fromisoformat(str(equity[0]["timestamp"])).timestamp())), 1.0
    )
    exposure_seconds = sum(
        max((t.exit_timestamp - t.entry_timestamp).total_seconds(), 0.0) for t in trades
    )
    equity_values = [Decimal(str(p["value"])) for p in equity if Decimal(str(p["value"])) > 0]
    avg_equity = sum(equity_values) / Decimal(len(equity_values)) if equity_values else Decimal("1")
    exposures = [(t.entry_price * t.quantity) / avg_equity * 100 for t in trades]
    return {
        "time_in_market_pct": round(min(exposure_seconds / total_seconds, 1.0) * 100, 8),
        "average_trade_exposure_pct": round(float(sum(exposures) / Decimal(len(exposures))), 8),
        "max_trade_exposure_pct": round(float(max(exposures)), 8),
    }


def risk_analytics(equity: Sequence[dict], trades: Sequence[BacktestTrade], initial: Decimal, final: Decimal) -> dict:
    dd = max_drawdown([Decimal(str(p["value"])) for p in equity])
    annual = annualized_return(initial, final, equity)
    vol = volatility([Decimal(str(p["value"])) for p in equity])
    return {
        "annualized_return_pct": round(float(annual * 100), 8),
        "volatility_pct": round(float(vol * 100), 8),
        "downside_volatility_pct": round(float(downside_volatility([Decimal(str(p["value"])) for p in equity]) * 100), 8),
        "calmar_ratio": round(float(annual / dd), 8) if dd else 0.0,
        "drawdown_periods": drawdown_periods(equity),
        "trade_statistics": trade_statistics(trades),
        "exposure": exposure_statistics(trades, equity),
    }
