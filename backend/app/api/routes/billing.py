"""Stripe billing routes."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.subscription import PlanTier, Subscription, SubscriptionStatus
from app.services.audit import log_audit
from app.services.stripe_service import (
    PLAN_CONFIG,
    create_checkout_session,
    create_portal_session,
    handle_webhook_event,
    map_stripe_plan,
    stripe_enabled,
)

router = APIRouter(prefix="/billing", tags=["Billing"])


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|pro)$")


class PlanInfo(BaseModel):
    id: str
    name: str
    price_usd: float
    features: List[str]
    stripe_enabled: bool


PLAN_FEATURES = {
    "free": ["2 strategies", "Paper trading", "Basic backtest"],
    "starter": ["5 strategies", "Paper + limited live", "Email alerts"],
    "pro": ["Unlimited strategies", "Full live trading", "AI insights", "Priority support"],
}


@router.get("/plans", response_model=List[PlanInfo])
async def list_plans():
    plans = [
        PlanInfo(
            id="free",
            name="Free",
            price_usd=0,
            features=PLAN_FEATURES["free"],
            stripe_enabled=stripe_enabled(),
        ),
    ]
    for plan_id, cfg in PLAN_CONFIG.items():
        plans.append(
            PlanInfo(
                id=plan_id,
                name=plan_id.capitalize(),
                price_usd=float(cfg["price_usd"]),
                features=PLAN_FEATURES.get(plan_id, []),
                stripe_enabled=stripe_enabled(),
            )
        )
    return plans


@router.get("/subscription")
async def get_subscription(current_user: CurrentUser, db: DbSession) -> Dict[str, Any]:
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return {"plan": "free", "status": "trial", "stripe_enabled": stripe_enabled()}
    return {
        "plan": sub.plan.value,
        "status": sub.status.value,
        "price": float(sub.price),
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "stripe_enabled": stripe_enabled(),
        "has_stripe_customer": bool(sub.stripe_customer_id),
    }


@router.post("/checkout")
async def create_checkout(
    data: CheckoutRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> Dict[str, str]:
    if not stripe_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing not configured. Set STRIPE_SECRET_KEY and price IDs in .env",
        )

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=current_user.id)
        db.add(sub)
        await db.flush()

    try:
        result = await create_checkout_session(
            user_email=current_user.email,
            user_id=str(current_user.id),
            plan=data.plan,
            customer_id=sub.stripe_customer_id,
        )
        await log_audit(db, action="billing.checkout", user_id=current_user.id, details={"plan": data.plan})
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/portal")
async def billing_portal(current_user: CurrentUser, db: DbSession) -> Dict[str, str]:
    if not stripe_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe not configured")
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No billing account found")
    try:
        return await create_portal_session(sub.stripe_customer_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request, db: DbSession):
    if not stripe_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = handle_webhook_event(payload, sig)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    event_type = event["type"]
    obj = event["data"]

    if event_type == "checkout.session.completed":
        user_id = obj.get("metadata", {}).get("user_id")
        plan = obj.get("metadata", {}).get("plan", "starter")
        customer_id = obj.get("customer")
        if user_id:
            await _update_subscription(
                db,
                uuid.UUID(user_id),
                plan,
                customer_id,
                obj.get("subscription"),
                SubscriptionStatus.ACTIVE,
            )

    elif event_type == "customer.subscription.updated":
        customer_id = obj.get("customer")
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "canceled": SubscriptionStatus.CANCELLED,
            "past_due": SubscriptionStatus.EXPIRED,
        }
        sub_status = status_map.get(obj.get("status"), SubscriptionStatus.ACTIVE)
        price_id = obj.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
        plan = map_stripe_plan(price_id)
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            subscription.plan = PlanTier(plan)
            subscription.status = sub_status
            subscription.stripe_subscription_id = obj.get("id")
            period_end = obj.get("current_period_end")
            if period_end:
                subscription.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    elif event_type == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.plan = PlanTier.FREE

    return {"received": True}


async def _update_subscription(
    db,
    user_id: uuid.UUID,
    plan: str,
    customer_id: str,
    subscription_id: str,
    status: SubscriptionStatus,
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=user_id)
        db.add(sub)

    tier_map = {
        "starter": PlanTier.STARTER,
        "pro": PlanTier.PRO,
        "enterprise": PlanTier.ENTERPRISE,
    }
    sub.plan = tier_map.get(plan, PlanTier.STARTER)
    sub.status = status
    sub.stripe_customer_id = customer_id
    sub.stripe_subscription_id = subscription_id
    sub.price = PLAN_CONFIG[plan]["price_usd"] if plan in PLAN_CONFIG else Decimal("0")
    sub.current_period_start = datetime.now(timezone.utc)
    await db.flush()
