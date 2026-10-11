"""Email service — SMTP with a safe development fallback."""

import logging
from html import escape
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send via SMTP; development fallback logs metadata only, never message content."""
    text_body = text_body or ""

    if not settings.smtp_user or not settings.smtp_password:
        if settings.app_env.strip().lower() not in {"development", "local", "test"}:
            logger.error("email_delivery_unavailable environment=%s", settings.app_env)
            return False
        logger.info("email_dev_delivery_skipped recipient_domain=%s subject=%s", to.rpartition("@")[2], subject)
        return False

    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_from
    message["To"] = to
    # Prevent CR/LF header injection and keep untrusted subjects bounded.
    message["Subject"] = subject.replace("\\r", " ").replace("\\n", " ")[:200]
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        return True
    except Exception:
        logger.error("email_delivery_failed recipient_domain=%s", to.rpartition("@")[2])
        return False


async def send_verification_email(to: str, token: str) -> bool:
    url = f"{settings.frontend_url}/verify-email?token={token}"
    html = f"""
    <h2>Verify your QuantForge account</h2>
    <p>Click the link below to verify your email:</p>
    <p><a href="{url}">Verify email</a></p>
    """
    return await send_email(to, "Verify your QuantForge email", html)


async def send_password_reset_email(to: str, token: str) -> bool:
    url = f"{settings.frontend_url}/reset-password?token={token}"
    html = f"""
    <h2>Reset your QuantForge password</h2>
    <p>Click the link below (expires in 1 hour):</p>
    <p><a href="{url}">Reset password</a></p>
    """
    return await send_email(to, "Reset your QuantForge password", html)


async def send_trade_alert_email(to: str, symbol: str, side: str, pnl: float) -> bool:
    safe_symbol = escape(str(symbol)[:32])
    safe_side = escape(str(side).upper()[:8])
    html = f"<p>Trade executed: <b>{safe_side}</b> {safe_symbol} | PnL: {pnl:.2f}</p>"
    return await send_email(to, f"Trade Alert: {str(symbol)[:32]}", html)
