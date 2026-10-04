"""AI insights routes."""

from typing import Any, Dict, List

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.portfolio import Portfolio
from app.models.strategy import Strategy

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/market-summary")
async def market_summary(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    return {
        "summary": (
            "Markets are showing mixed signals with tech leading gains while energy "
            "sectors face headwinds. Volatility remains elevated — favor defensive position sizing."
        ),
        "sentiment": "neutral-bullish",
        "confidence": 0.78,
        "key_levels": {"SPY": {"support": 512, "resistance": 528}, "BTC": {"support": 64000, "resistance": 70000}},
        "generated_at": "2026-05-22T12:00:00Z",
    }


@router.get("/risk-analysis")
async def risk_analysis(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolios = result.scalars().all()
    total_exposure = sum(float(p.risk_exposure) for p in portfolios) / max(len(portfolios), 1)

    return {
        "overall_risk_score": min(total_exposure / 20 * 10, 10),
        "risk_level": "moderate" if total_exposure < 15 else "high",
        "recommendations": [
            "Diversify across uncorrelated asset classes",
            "Reduce leverage if exposure exceeds 15%",
            "Set trailing stops on open winning positions",
        ],
        "var_95": round(total_exposure * 1000, 2),
        "max_drawdown_alert": total_exposure > 20,
    }


@router.get("/portfolio-analysis")
async def portfolio_analysis(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id))
    portfolios = result.scalars().all()
    total_value = sum(float(p.total_value) for p in portfolios)

    return {
        "total_value": total_value,
        "diversification_score": 7.2,
        "insights": [
            "Portfolio concentration in tech exceeds 40% — consider rebalancing",
            "Cash allocation at 22% provides good dry powder for opportunities",
            "3 strategies are correlated — reduce overlap for smoother equity curve",
        ],
        "suggested_actions": ["rebalance", "reduce_correlation", "increase_cash_buffer"],
    }


@router.get("/trade-journal")
async def trade_journal(current_user: CurrentUser, db: DbSession, limit: int = 5) -> List[Dict[str, Any]]:
    return [
        {
            "date": "2026-05-21",
            "reflection": "Entered AAPL on EMA crossover — good discipline on stop loss.",
            "lesson": "Wait for volume confirmation before sizing up.",
            "emotion_score": "calm",
        },
        {
            "date": "2026-05-20",
            "reflection": "Exited BTC position early due to fear — missed continuation.",
            "lesson": "Trust the system; avoid discretionary overrides.",
            "emotion_score": "anxious",
        },
    ][:limit]
