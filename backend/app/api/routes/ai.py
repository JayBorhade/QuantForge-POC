"""Derived intelligence endpoints.

These endpoints intentionally avoid fabricated market data. They expose only
insights that can be derived from QuantForge's persisted portfolio state.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.trade import Trade, TradeStatus
from app.services.risk_analytics import RiskAnalyticsService

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/market-summary")
async def market_summary(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    return {
        "summary": "Live market intelligence is not connected to this deployment.",
        "sentiment": "unavailable",
        "confidence": 0.0,
        "key_levels": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/risk-analysis")
async def risk_analysis(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolios = list(result.scalars().all())
    summaries = [await RiskAnalyticsService(db).summarize(p) for p in portfolios]

    utilizations = [
        u for summary in summaries
        for u in (
            summary.gross_utilization,
            summary.daily_loss_utilization,
            summary.open_order_utilization,
        )
        if u is not None
    ]
    peak = max(utilizations, default=0)
    score = min(float(peak) * 10, 10)
    if score >= 8:
        level = "high"
    elif score >= 5:
        level = "moderate"
    else:
        level = "low"

    recommendations: list[str] = []
    if not summaries:
        recommendations.append("Create an active portfolio and configure explicit risk limits.")
    elif not utilizations:
        recommendations.append("Configure gross exposure, daily loss, or open-order limits to enable utilization monitoring.")
    elif peak >= 1:
        recommendations.append("At least one configured risk limit is fully utilized; reduce exposure before placing additional orders.")
    else:
        recommendations.append("Configured portfolio risk utilization is currently below its limits.")

    return {
        "overall_risk_score": round(score, 2),
        "risk_level": level,
        "recommendations": recommendations,
        "var_95": None,
        "max_drawdown_alert": any(
            summary.daily_loss_utilization is not None and summary.daily_loss_utilization >= 1
            for summary in summaries
        ),
    }


@router.get("/portfolio-analysis")
async def portfolio_analysis(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    portfolios_result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolios = list(portfolios_result.scalars().all())
    portfolio_ids = [p.id for p in portfolios]

    positions_result = await db.execute(
        select(Position).where(Position.portfolio_id.in_(portfolio_ids))
    ) if portfolio_ids else None
    positions = list(positions_result.scalars().all()) if positions_result else []

    total_value = sum((p.total_value for p in portfolios), 0)
    by_symbol: dict[str, float] = {}
    for position in positions:
        by_symbol[position.symbol] = by_symbol.get(position.symbol, 0.0) + abs(
            float(position.quantity * position.average_cost)
        )

    concentration = (
        max(by_symbol.values()) / float(total_value)
        if by_symbol and total_value > 0
        else 0.0
    )
    return {
        "total_value": float(total_value),
        "diversification_score": round(max(0.0, min(10.0, 10 * (1 - concentration))), 2),
        "insights": [
            f"Largest symbol concentration is {concentration:.1%}."
            if by_symbol else "No open positions are available for concentration analysis.",
            f"{len(by_symbol)} symbols are currently represented across open positions.",
        ],
        "suggested_actions": (
            ["review_symbol_concentration"] if concentration > 0.40 else ["maintain_current_allocation"]
        ),
    }


@router.get("/trade-journal")
async def trade_journal(current_user: CurrentUser, db: DbSession, limit: int = 5) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 50))
    result = await db.execute(
        select(Trade)
        .join(Portfolio)
        .where(
            Portfolio.user_id == current_user.id,
            Trade.status == TradeStatus.CLOSED,
        )
        .order_by(Trade.closed_at.desc().nullslast(), Trade.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "date": (trade.closed_at or trade.created_at).isoformat(),
            "reflection": f"{trade.side.value.upper()} {trade.symbol} closed with {float(trade.pnl or 0):.2f} P&L.",
            "lesson": "Review execution and risk settings against the recorded result.",
            "emotion_score": "unavailable",
        }
        for trade in result.scalars().all()
    ]
