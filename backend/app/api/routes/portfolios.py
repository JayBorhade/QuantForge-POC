"""Portfolio management routes."""

import uuid
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.brokers.factory import get_broker_adapter
from app.core.encryption import decrypt_credentials
from app.models.broker_token import BrokerToken, BrokerType
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.trade import Trade
from app.services.audit import log_audit
from app.services.portfolio_valuation import PortfolioValuationError, PortfolioValuationService

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    currency: str = "USD"
    initial_capital: float = Field(default=100000.0, gt=0)


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    total_value: float
    cash_balance: float
    daily_pnl: float
    total_pnl: float
    risk_exposure: float
    win_rate: float
    status: str
    broker: str | None

    model_config = {"from_attributes": True}


def _to_response(p: Portfolio) -> PortfolioResponse:
    return PortfolioResponse(
        id=p.id,
        name=p.name,
        currency=p.currency,
        total_value=float(p.total_value),
        cash_balance=float(p.cash_balance),
        daily_pnl=float(p.daily_pnl),
        total_pnl=float(p.total_pnl),
        risk_exposure=float(p.risk_exposure),
        win_rate=float(p.win_rate),
        status=p.status.value,
        broker=p.broker,
    )


@router.get("", response_model=List[PortfolioResponse])
async def list_portfolios(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id).order_by(Portfolio.created_at)
    )
    return [_to_response(p) for p in result.scalars().all()]


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(data: PortfolioCreate, current_user: CurrentUser, db: DbSession):
    portfolio = Portfolio(
        user_id=current_user.id,
        name=data.name,
        currency=data.currency,
        total_value=Decimal(str(data.initial_capital)),
        cash_balance=Decimal(str(data.initial_capital)),
    )
    db.add(portfolio)
    await log_audit(db, action="portfolio.create", user_id=current_user.id)
    await db.flush()
    await db.refresh(portfolio)
    return _to_response(portfolio)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    portfolio = await _get_portfolio(db, portfolio_id, current_user.id)
    return _to_response(portfolio)


@router.get("/{portfolio_id}/valuation")
async def portfolio_valuation(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    broker: str = "binance",
):
    """Mark all open positions to current broker prices and persist portfolio equity."""
    portfolio = await _get_portfolio(db, portfolio_id, current_user.id)
    try:
        broker_type = BrokerType(broker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsupported broker") from exc

    token_result = await db.execute(
        select(BrokerToken).where(
            BrokerToken.user_id == current_user.id,
            BrokerToken.broker == broker_type,
            BrokerToken.is_active.is_(True),
        )
    )
    token = token_result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=404, detail="Connected broker not found")

    try:
        credentials = decrypt_credentials(token.api_secret_encrypted)
        adapter = get_broker_adapter(
            broker_type.value,
            credentials["api_key"],
            credentials["api_secret"],
            credentials.get("access_token"),
        )

        if broker_type is not BrokerType.BINANCE:
            raise HTTPException(
                status_code=400,
                detail="Portfolio valuation currently requires a broker with symbol-only quote support; Binance is supported in this endpoint.",
            )

        valuation = await PortfolioValuationService(db, adapter).value_portfolio(portfolio)
    except HTTPException:
        raise
    except PortfolioValuationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Broker valuation request failed: {exc}") from exc

    return {
        "portfolio_id": valuation.portfolio_id,
        "cash_balance": float(valuation.cash_balance),
        "position_market_value": float(valuation.position_market_value),
        "equity": float(valuation.equity),
        "realized_pnl": float(valuation.realized_pnl),
        "unrealized_pnl": float(valuation.unrealized_pnl),
        "total_pnl": float(valuation.total_pnl),
        "gross_exposure": float(valuation.gross_exposure),
        "risk_exposure": float(valuation.risk_exposure),
        "positions": [
            {
                "symbol": item.symbol,
                "quantity": float(item.quantity),
                "average_cost": float(item.average_cost),
                "market_price": float(item.market_price),
                "market_value": float(item.market_value),
                "unrealized_pnl": float(item.unrealized_pnl),
                "realized_pnl": float(item.realized_pnl),
            }
            for item in valuation.positions
        ],
    }


@router.get("/{portfolio_id}/analytics")
async def portfolio_analytics(portfolio_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    portfolio = await _get_portfolio(db, portfolio_id, current_user.id)
    trades_result = await db.execute(
        select(Trade).where(Trade.portfolio_id == portfolio.id).order_by(Trade.created_at.desc()).limit(50)
    )
    trades = trades_result.scalars().all()
    closed = [t for t in trades if t.pnl is not None]
    wins = [t for t in closed if t.pnl and t.pnl > 0]

    return {
        "portfolio_id": str(portfolio.id),
        "allocation": {
            "equity": float(portfolio.total_value - portfolio.cash_balance),
            "cash": float(portfolio.cash_balance),
        },
        "performance": {
            "total_pnl": float(portfolio.total_pnl),
            "daily_pnl": float(portfolio.daily_pnl),
            "win_rate": float(portfolio.win_rate),
        },
        "recent_trades": [
            {
                "id": str(t.id),
                "symbol": t.symbol,
                "side": t.side.value,
                "pnl": float(t.pnl) if t.pnl else None,
                "status": t.status.value,
            }
            for t in trades[:10]
        ],
        "metrics": {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(closed) - len(wins),
        },
    }


async def _get_portfolio(db, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio
