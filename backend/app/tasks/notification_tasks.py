"""Notification Celery tasks."""

import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def send_email_notification(user_id: str, subject: str, body: str):
    logger.info("Sending email to user %s: %s", user_id, subject)
    # SMTP integration placeholder - wired via env vars in production
    return {"sent": True, "user_id": user_id}


@celery_app.task
def send_trade_alert(user_id: str, trade_data: dict):
    logger.info("Trade alert for user %s: %s", user_id, trade_data)
    return {"alert_sent": True}
