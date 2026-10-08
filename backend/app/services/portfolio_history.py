"""Portfolio history and performance analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.portfolio_valuation import PortfolioValuation


class PortfolioHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_snapshot(
        self, portfolio: Portfolio, valuation: PortfolioValuation, *, recorded_at: datetime | None = None
    ) -> PortfolioSnapshot:
        now = recorded_at or datetime.now(timezone.utc)
        previous = await self.db.execute(
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.recorded_at < now,
            )
            .order_by(PortfolioSnapshot.recorded_at.desc())
            .limit(1)
        )
        previous_snapshot = previous.scalar_one_or_none()
        prior_equity = previous_snapshot.equity if previous_snapshot else portfolio.total_value

        if prior_equity and prior_equity > 0:
            daily_return = (valuation.equity - prior_equity) / prior_equity
        else:
            daily_return = Decimal("0")

        peak_result = await self.db.execute(
            select(PortfolioSnapshot.equity)
            .where(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.recorded_at <= now,
            )
            .order_by(PortfolioSnapshot.equity.desc())
            .limit(1)
        )
        peak = peak_result.scalar_one_or_none() or valuation.equity
        drawdown = (valuation.equity - peak) / peak if peak > 0 else Decimal("0")

        snapshot = PortfolioSnapshot(
            portfolio_id=portfolio.id,
            recorded_at=now,
            equity=valuation.equity,
            cash_balance=valuation.cash_balance,
            position_market_value=valuation.position_market_value,
            realized_pnl=valuation.realized_pnl,
            unrealized_pnl=valuation.unrealized_pnl,
            total_pnl=valuation.total_pnl,
            daily_return=daily_return,
            drawdown=drawdown,
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def history(
        self, portfolio_id, *, start: datetime | None = None, end: datetime | None = None, limit: int = 500
    ) -> list[PortfolioSnapshot]:
        stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio_id)
        if start is not None:
            stmt = stmt.where(PortfolioSnapshot.recorded_at >= start)
        if end is not None:
            stmt = stmt.where(PortfolioSnapshot.recorded_at <= end)
        stmt = stmt.order_by(PortfolioSnapshot.recorded_at.asc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def metrics(self, portfolio_id, *, days: int = 30) -> dict:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        snapshots = await self.history(portfolio_id, start=start, end=end, limit=5000)
        if not snapshots:
            return {
                "period_days": days,
                "observations": 0,
                "return": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "volatility": Decimal("0"),
                "best_period_return": Decimal("0"),
                "worst_period_return": Decimal("0"),
            }

        first, last = snapshots[0], snapshots[-1]
        period_return = (
            (last.equity - first.equity) / first.equity if first.equity > 0 else Decimal("0")
        )
        returns = [s.daily_return for s in snapshots]
        mean = sum(returns, Decimal("0")) / Decimal(len(returns))
        variance = sum((r - mean) ** 2 for r in returns) / Decimal(len(returns))
        volatility = variance.sqrt() if variance >= 0 else Decimal("0")

        return {
            "period_days": days,
            "observations": len(snapshots),
            "return": period_return,
            "max_drawdown": min((s.drawdown for s in snapshots), default=Decimal("0")),
            "volatility": volatility,
            "best_period_return": max(returns, default=Decimal("0")),
            "worst_period_return": min(returns, default=Decimal("0")),
        }
