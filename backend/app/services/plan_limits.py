"""Server-enforced per-plan resource ceilings.

Limits intentionally remain finite for every tier until paid entitlements and
operational capacity have been proven. UI copy is not an authorization control.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.strategy import Strategy
from app.models.subscription import PlanTier, Subscription, SubscriptionStatus


@dataclass(frozen=True)
class ResourceLimits:
    strategies: int
    portfolios: int


PLAN_LIMITS = {
    PlanTier.FREE: ResourceLimits(strategies=2, portfolios=1),
    PlanTier.STARTER: ResourceLimits(strategies=5, portfolios=3),
    PlanTier.PRO: ResourceLimits(strategies=20, portfolios=10),
    PlanTier.ENTERPRISE: ResourceLimits(strategies=100, portfolios=50),
}


async def get_effective_limits(db: AsyncSession, user_id) -> ResourceLimits:
    """Use paid limits only for an active subscription; default to free limits."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        return PLAN_LIMITS[PlanTier.FREE]
    if subscription.plan is PlanTier.FREE:
        return PLAN_LIMITS[PlanTier.FREE]
    if subscription.status is not SubscriptionStatus.ACTIVE:
        return PLAN_LIMITS[PlanTier.FREE]
    return PLAN_LIMITS.get(subscription.plan, PLAN_LIMITS[PlanTier.FREE])


async def count_user_resource(db: AsyncSession, user_id, resource: str) -> int:
    """Count one of the supported per-user resource types."""
    if resource == "strategies":
        statement = select(func.count(Strategy.id)).where(Strategy.user_id == user_id)
    elif resource == "portfolios":
        statement = select(func.count(Portfolio.id)).where(Portfolio.user_id == user_id)
    else:
        raise ValueError("Unsupported resource type")
    result = await db.execute(statement)
    return int(result.scalar_one())
