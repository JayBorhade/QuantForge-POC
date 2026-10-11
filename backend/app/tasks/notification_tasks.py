"""Email notification Celery tasks with real delivery status."""

import asyncio
import logging
from decimal import Decimal, InvalidOperation
from html import escape

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _user_email(user_id: str) -> str | None:
    """Resolve a recipient from the database; never trust an email in task input."""
    import uuid

    from app.db.sync_session import get_sync_db
    from app.models.user import User

    with get_sync_db() as db:
        user = db.get(User, uuid.UUID(user_id))
        return user.email if user and user.is_active and not user.is_banned else None


@celery_app.task(bind=True, max_retries=2)
def send_email_notification(self, user_id: str, subject: str, body: str):
    """Deliver an email and return the actual delivery result, never fake success."""
    try:
        recipient = _user_email(user_id)
        if not recipient:
            return {"sent": False, "reason": "recipient_unavailable"}
        from app.services.email import send_email

        safe_subject = str(subject)[:200]
        safe_body = escape(str(body)[:20000]).replace("\\n", "<br>")
        sent = asyncio.run(
            send_email(
                recipient,
                safe_subject,
                f"<div>{safe_body}</div>",
                text_body=str(body)[:20000],
            )
        )
        if not sent:
            logger.warning("notification_delivery_unavailable user_id=%s", user_id)
        return {"sent": bool(sent), "user_id": user_id}
    except Exception as exc:
        logger.error("notification_task_failed user_id=%s error_type=%s", user_id, type(exc).__name__)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2)
def send_trade_alert(self, user_id: str, trade_data: dict):
    """Send a validated trade alert without logging financial payloads."""
    try:
        recipient = _user_email(user_id)
        if not recipient:
            return {"alert_sent": False, "reason": "recipient_unavailable"}

        from app.services.email import send_trade_alert_email

        symbol = str(trade_data.get("symbol", ""))[:32].strip()
        side = str(trade_data.get("side", ""))[:8].strip()
        if not symbol or side.lower() not in {"buy", "sell"}:
            return {"alert_sent": False, "reason": "invalid_trade_data"}
        try:
            pnl = Decimal(str(trade_data.get("pnl", 0)))
        except (InvalidOperation, TypeError, ValueError):
            return {"alert_sent": False, "reason": "invalid_trade_data"}
        if not pnl.is_finite():
            return {"alert_sent": False, "reason": "invalid_trade_data"}

        sent = asyncio.run(send_trade_alert_email(recipient, symbol, side, float(pnl)))
        if not sent:
            logger.warning("trade_alert_delivery_unavailable user_id=%s", user_id)
        return {"alert_sent": bool(sent), "user_id": user_id}
    except Exception as exc:
        logger.error("trade_alert_task_failed user_id=%s error_type=%s", user_id, type(exc).__name__)
        raise self.retry(exc=exc, countdown=60)
