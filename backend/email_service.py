"""Password-reset email via Resend API (preferred) or SMTP. Never expose reset tokens to clients."""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

logger = logging.getLogger(__name__)

SUBJECT = "CauseSense AI — Reset your password"


def email_configured() -> bool:
    """True when at least one delivery channel is configured."""
    if os.environ.get("RESEND_API_KEY"):
        return True
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def _body_text(reset_url: str) -> str:
    return f"""Hello,

We received a request to reset your CauseSense AI password.

Open this link to choose a new password (valid for 1 hour):
{reset_url}

If you did not request this, you can ignore this email. Your password will stay the same.

— CauseSense AI
"""


def _body_html(reset_url: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;line-height:1.5;color:#111">
  <p>Hello,</p>
  <p>We received a request to reset your <strong>CauseSense AI</strong> password.</p>
  <p><a href="{reset_url}" style="display:inline-block;padding:10px 16px;background:#0f766e;color:#fff;text-decoration:none;border-radius:6px">Reset password</a></p>
  <p style="font-size:13px;color:#555">Or copy this link (expires in 1 hour):<br/>{reset_url}</p>
  <p style="font-size:13px;color:#555">If you did not request this, ignore this email.</p>
  <p>— CauseSense AI</p>
</body></html>
"""


def send_via_resend(to_email: str, reset_url: str) -> bool:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        return False

    from_addr = os.environ.get(
        "EMAIL_FROM",
        os.environ.get("SMTP_FROM", "CauseSense AI <onboarding@resend.dev>"),
    )

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [to_email],
                "subject": SUBJECT,
                "text": _body_text(reset_url),
                "html": _body_html(reset_url),
            },
            timeout=20.0,
        )
        if resp.status_code in (200, 201):
            logger.info("Password reset email sent via Resend to %s", to_email)
            return True
        logger.error("Resend failed (%s): %s", resp.status_code, resp.text[:500])
        return False
    except Exception as e:
        logger.error("Resend request error: %s", e)
        return False


def send_via_smtp(to_email: str, reset_url: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ.get("SMTP_FROM") or os.environ.get("EMAIL_FROM")
    use_tls = os.environ.get("SMTP_TLS", "true").lower() in ("1", "true", "yes")

    if not host or not from_addr:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = SUBJECT
    msg.attach(MIMEText(_body_text(reset_url), "plain"))
    msg.attach(MIMEText(_body_html(reset_url), "html"))

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        logger.info("Password reset email sent via SMTP to %s", to_email)
        return True
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        return False


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Try Resend first, then SMTP. Never logs the raw reset URL."""
    if send_via_resend(to_email, reset_url):
        return True
    if send_via_smtp(to_email, reset_url):
        return True
    logger.error(
        "Password reset email NOT sent to %s — set RESEND_API_KEY or SMTP_* on the API service",
        to_email,
    )
    return False
