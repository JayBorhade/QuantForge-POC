"""Dashboard routes."""

from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.portfolio import Portfolio
from app.models.strategy import Strategy, StrategyStatus
from app.models.trade import Trade, TradeStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def get_overview(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    portfolios_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolios = portfolios_result.scalars().all()

    total_value = sum(p.total_value for p in portfolios) or Decimal("0")
    daily_pnl = sum(p.daily_pnl for p in portfolios) or Decimal("0")
    risk_exposure = sum(p.risk_exposure for p in portfolios) / max(len(portfolios), 1)

    strategies_result = await db.execute(
        select(func.count(Strategy.id)).where(
            Strategy.user_id == current_user.id,
            Strategy.status == StrategyStatus.ACTIVE,
        )
    )
    active_bots = strategies_result.scalar() or 0

    trades_result = await db.execute(
        select(func.count(Trade.id)).where(
            Trade.status == TradeStatus.OPEN,
            Trade.portfolio_id.in_(
                select(Portfolio.id).where(Portfolio.user_id == current_user.id)
            ),
        )
    )
    open_trades = trades_result.scalar() or 0

    win_rates = [float(p.win_rate) for p in portfolios if p.win_rate]
    avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0.0

    return {
        "portfolio_value": float(total_value),
        "daily_pnl": float(daily_pnl),
        "active_bots": active_bots,
        "open_trades": open_trades,
        "risk_exposure": float(risk_exposure),
        "win_rate": avg_win_rate,
        "market_sentiment": "bullish",
        "ai_suggestions": [
            {
                "type": "risk",
                "message": "Consider reducing position size on high-volatility symbols.",
                "confidence": 0.82,
            },
            {
                "type": "opportunity",
                "message": "EMA crossover signal detected on AAPL — review strategy.",
                "confidence": 0.71,
            },
        ],
    }


@router.get("/recent-trades")
async def get_recent_trades(current_user: CurrentUser, db: DbSession, limit: int = 10) -> List[Dict]:
    result = await db.execute(
        select(Trade)
        .join(Portfolio)
        .where(Portfolio.user_id == current_user.id)
        .order_by(Trade.created_at.desc())
        .limit(limit)
    )
    trades = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "symbol": t.symbol,
            "side": t.side.value,
            "status": t.status.value,
            "pnl": float(t.pnl) if t.pnl else None,
            "quantity": float(t.quantity),
            "created_at": t.created_at.isoformat(),
        }
        for t in trades
    ]
