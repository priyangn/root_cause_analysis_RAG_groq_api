"""Optional email sending for password reset. Falls back to in-app reset link when SMTP is unset."""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def email_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Send reset email via SMTP. Returns True on success."""
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ.get("SMTP_FROM")
    use_tls = os.environ.get("SMTP_TLS", "true").lower() in ("1", "true", "yes")

    if not host or not from_addr:
        logger.info("SMTP not configured — skip email to %s", to_email)
        return False

    subject = "CauseSense AI — Reset your password"
    body = f"""Hello,

We received a request to reset your CauseSense AI password.

Open this link to choose a new password (valid for 1 hour):
{reset_url}

If you did not request this, you can ignore this email.

— CauseSense AI
"""

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        logger.info("Password reset email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send reset email: %s", e)
        return False
