"""Email service — SMTP with dev console fallback."""

import logging
from typing import Optional

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send email via SMTP. Logs to console in dev when SMTP not configured."""
    text_body = text_body or html_body

    if not settings.smtp_user or not settings.smtp_password:
        logger.info(
            "[EMAIL DEV] To: %s | Subject: %s\n%s",
            to,
            subject,
            text_body[:500],
        )
        return True

    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
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
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return False


async def send_verification_email(to: str, token: str) -> bool:
    url = f"{settings.frontend_url}/verify-email?token={token}"
    html = f"""
    <h2>Verify your QuantForge account</h2>
    <p>Click the link below to verify your email:</p>
    <p><a href="{url}">{url}</a></p>
    """
    return await send_email(to, "Verify your QuantForge email", html)


async def send_password_reset_email(to: str, token: str) -> bool:
    url = f"{settings.frontend_url}/reset-password?token={token}"
    html = f"""
    <h2>Reset your QuantForge password</h2>
    <p>Click the link below (expires in 1 hour):</p>
    <p><a href="{url}">{url}</a></p>
    """
    return await send_email(to, "Reset your QuantForge password", html)


async def send_trade_alert_email(to: str, symbol: str, side: str, pnl: float) -> bool:
    html = f"<p>Trade executed: <b>{side.upper()}</b> {symbol} | PnL: {pnl:.2f}</p>"
    return await send_email(to, f"Trade Alert: {symbol}", html)
