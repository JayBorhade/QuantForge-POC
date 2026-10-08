"""Deterministic performance metrics."""
from decimal import Decimal
from math import sqrt
from statistics import mean, pstdev
from typing import Sequence

def total_return(initial: Decimal, final: Decimal) -> Decimal:
    return (final - initial) / initial if initial else Decimal("0")

def max_drawdown(equity: Sequence[Decimal]) -> Decimal:
    if not equity: return Decimal("0")
    peak, result = equity[0], Decimal("0")
    for value in equity:
        peak = max(peak, value)
        if peak > 0: result = max(result, (peak - value) / peak)
    return result

def sharpe_ratio(equity: Sequence[Decimal], annual_periods: int = 252) -> Decimal:
    if len(equity) < 3: return Decimal("0")
    returns = [(equity[i] / equity[i-1]) - Decimal("1") for i in range(1, len(equity)) if equity[i-1] > 0]
    if len(returns) < 2: return Decimal("0")
    values = [float(x) for x in returns]
    deviation = pstdev(values)
    if deviation == 0: return Decimal("0")
    return Decimal(str(mean(values) / deviation * sqrt(annual_periods)))

def win_rate(wins: int, total: int) -> Decimal:
    return Decimal(wins) / Decimal(total) if total else Decimal("0")
