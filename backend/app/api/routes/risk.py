"""Portfolio risk configuration and exposure endpoints."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.portfolio import Portfolio
from app.models.risk_limit import RiskLimit
from app.services.audit import log_audit

router = APIRouter(prefix="/risk", tags=["Risk"])


class RiskLimitUpdate(BaseModel):
    max_order_notional: Decimal | None = Field(default=None, ge=0)
    max_position_quantity: Decimal | None = Field(default=None, gt=0)
    max_daily_loss: Decimal | None = Field(default=None, gt=0)
    max_open_orders: int | None = Field(default=None, ge=1)
    max_gross_exposure: Decimal | None = Field(default=None, gt=0)
    max_symbol_exposure: Decimal | None = Field(default=None, gt=0)
    max_strategy_exposure: Decimal | None = Field(default=None, gt=0)
    max_strategy_allocation_pct: Decimal | None = Field(default=None, gt=0, le=1)
    kill_switch: bool = False

    @model_validator(mode="after")
    def validate_order_limit(self):
        if (
            self.max_order_notional is not None
            and self.max_gross_exposure is not None
            and self.max_order_notional > self.max_gross_exposure
        ):
            raise ValueError("max_order_notional cannot exceed max_gross_exposure")
        return self


class RiskLimitResponse(RiskLimitUpdate):
    portfolio_id: uuid.UUID
    updated_at: str


async def _get_portfolio(db, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


def _response(limit: RiskLimit, portfolio_id: uuid.UUID) -> RiskLimitResponse:
    return RiskLimitResponse(
        portfolio_id=portfolio_id,
        max_order_notional=limit.max_order_notional,
        max_position_quantity=limit.max_position_quantity,
        max_daily_loss=limit.max_daily_loss,
        max_open_orders=limit.max_open_orders,
        max_gross_exposure=limit.max_gross_exposure,
        max_symbol_exposure=limit.max_symbol_exposure,
        max_strategy_exposure=limit.max_strategy_exposure,
        max_strategy_allocation_pct=limit.max_strategy_allocation_pct,
        kill_switch=limit.kill_switch,
        updated_at=limit.updated_at.isoformat(),
    )


@router.get("/{portfolio_id}", response_model=RiskLimitResponse | None)
async def get_risk_limits(portfolio_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    portfolio = await _get_portfolio(db, portfolio_id, current_user.id)
    result = await db.execute(select(RiskLimit).where(RiskLimit.portfolio_id == portfolio.id))
    limit = result.scalar_one_or_none()
    return _response(limit, portfolio.id) if limit else None


@router.put("/{portfolio_id}", response_model=RiskLimitResponse)
async def update_risk_limits(
    portfolio_id: uuid.UUID,
    data: RiskLimitUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    portfolio = await _get_portfolio(db, portfolio_id, current_user.id)
    result = await db.execute(select(RiskLimit).where(RiskLimit.portfolio_id == portfolio.id))
    limit = result.scalar_one_or_none()
    if limit is None:
        limit = RiskLimit(portfolio_id=portfolio.id)
        db.add(limit)

    for field, value in data.model_dump().items():
        setattr(limit, field, value)

    await db.flush()
    await log_audit(
        db,
        action="risk_limits.update",
        user_id=current_user.id,
        resource="portfolio",
        resource_id=str(portfolio.id),
        details={"kill_switch": limit.kill_switch},
    )
    await db.refresh(limit)
    return _response(limit, portfolio.id)
