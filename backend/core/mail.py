"""Minimal SMTP sender. Email is optional; callers check `get_settings().email_enabled`."""

import logging
import smtplib
from email.message import EmailMessage

from backend.core.config import get_settings

logger = logging.getLogger("mail")


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns False (and logs) on failure instead of raising."""
    s = get_settings()
    if not s.email_enabled:
        return False

    msg = EmailMessage()
    msg["From"] = s.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=15) as smtp:
            if s.SMTP_STARTTLS:
                smtp.starttls()
            if s.SMTP_USERNAME:
                smtp.login(s.SMTP_USERNAME, s.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to send email to %s", to)
        return False
