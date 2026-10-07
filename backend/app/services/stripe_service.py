"""Stripe billing integration."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PLAN_CONFIG = {
    "starter": {
        "tier": "starter",
        "price_usd": Decimal("29.00"),
        "stripe_price_id": lambda: settings.stripe_price_starter,
    },
    "pro": {
        "tier": "pro",
        "price_usd": Decimal("99.00"),
        "stripe_price_id": lambda: settings.stripe_price_pro,
    },
}


def stripe_enabled() -> bool:
    return bool(settings.stripe_secret_key and settings.stripe_secret_key.startswith("sk_"))


def get_stripe():
    if not stripe_enabled():
        raise RuntimeError("Stripe is not configured")
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


async def create_checkout_session(
    user_email: str,
    user_id: str,
    plan: str,
    customer_id: Optional[str] = None,
) -> Dict[str, Any]:
    if plan not in PLAN_CONFIG:
        raise ValueError(f"Invalid plan: {plan}")

    price_id = PLAN_CONFIG[plan]["stripe_price_id"]()
    if not price_id:
        raise RuntimeError(f"Stripe price ID not configured for plan: {plan}")

    stripe = get_stripe()

    session_params: Dict[str, Any] = {
        "mode": "subscription",
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{settings.frontend_url}/dashboard/settings?billing=success",
        "cancel_url": f"{settings.frontend_url}/pricing?billing=cancelled",
        "metadata": {"user_id": user_id, "plan": plan},
        "customer_email": user_email if not customer_id else None,
    }
    if customer_id:
        session_params["customer"] = customer_id
        del session_params["customer_email"]

    session = stripe.checkout.Session.create(**session_params)
    return {"checkout_url": session.url, "session_id": session.id}


async def create_portal_session(customer_id: str) -> Dict[str, str]:
    stripe = get_stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/dashboard/settings",
    )
    return {"portal_url": session.url}


def handle_webhook_event(payload: bytes, sig_header: str) -> Dict[str, Any]:
    stripe = get_stripe()
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )
    return {"type": event.type, "data": event.data.object}


def map_stripe_plan(price_id: Optional[str]) -> str:
    if price_id == settings.stripe_price_pro:
        return "pro"
    if price_id == settings.stripe_price_starter:
        return "starter"
    return "free"
