"""Minimal transactional email helper.

Sends via SMTP when configured; otherwise falls back to a "console backend"
that logs the message (handy for local dev). Nothing here raises to callers —
email is best-effort and must never break the request that triggered it.
"""

import html as html_lib
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NewEventEmail:
    """Everything needed to email followers about a newly published event.

    Plain data (no ORM objects) so it can be handed to a background task after
    the request's DB session has closed.
    """

    event_id: int
    event_title: str
    event_start: datetime
    calendar_name: str
    recipient_emails: list[str]


def _text_body(msg: EmailMessage) -> str:
    """Return the plain-text part of a message (multipart-safe)."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_content()
        return "(no text/plain part)"
    return msg.get_content()


def _deliver(msg: EmailMessage) -> bool:
    """Send one message via SMTP, or log it if email isn't configured.

    Returns True on (apparent) success, False on failure. Never raises.
    """
    to = msg["To"]

    if not settings.EMAIL_ENABLED or not settings.SMTP_HOST:
        # Console backend — log instead of sending.
        logger.info(
            "[email:console] To=%s Subject=%s\n%s",
            to,
            msg["Subject"],
            _text_body(msg),
        )
        return True

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_TLS:
                smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("[email] Sent to %s (subject=%s)", to, msg["Subject"])
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort; log and move on.
        logger.error("[email] Failed to send to %s: %s", to, exc)
        return False


def send_email(*, to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Compose and deliver a single email. Returns True on success."""
    msg = EmailMessage()
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    return _deliver(msg)


def send_new_event_emails(batch: NewEventEmail) -> None:
    """Email each follower that a new event was published on their calendar.

    Designed to run in a background task. Logs an aggregate success/failure
    summary.
    """
    if not batch.recipient_emails:
        return

    event_url = f"{settings.FRONTEND_URL}/events/{batch.event_id}"
    when = batch.event_start.strftime("%a %d %b %Y, %H:%M")
    subject = f"New event: {batch.event_title}"

    text = (
        f"{batch.calendar_name} just published a new event.\n\n"
        f"{batch.event_title}\n"
        f"When: {when}\n\n"
        f"View it here: {event_url}\n"
    )
    html = (
        f'<p><strong>{batch.calendar_name}</strong> just published a new event.</p>'
        f'<h2 style="margin:0 0 8px">{batch.event_title}</h2>'
        f'<p style="color:#6b7280;margin:0 0 16px">When: {when}</p>'
        f'<p><a href="{event_url}" '
        f'style="display:inline-block;padding:10px 18px;background:#7c3aed;'
        f'color:#fff;border-radius:9999px;text-decoration:none">View event</a></p>'
    )

    sent = sum(
        send_email(to=addr, subject=subject, text=text, html=html)
        for addr in batch.recipient_emails
    )
    logger.info(
        "[email] new-event batch for event %s: %d/%d delivered.",
        batch.event_id,
        sent,
        len(batch.recipient_emails),
    )


def send_event_message(
    *,
    subject: str,
    body: str,
    recipients: list[str],
    event_id: int,
    event_title: str,
) -> None:
    """Broadcast an organizer's message to an event's guests.

    Designed to run in a background task. Logs an aggregate summary.
    """
    if not recipients:
        return

    event_url = f"{settings.FRONTEND_URL}/events/{event_id}"
    text = (
        f"{body}\n\n"
        f"—\nRegarding: {event_title}\n{event_url}\n"
    )
    html = (
        f'<div style="white-space:pre-wrap">{html_lib.escape(body)}</div>'
        f'<hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">'
        f'<p style="color:#6b7280;font-size:14px">Regarding '
        f'<a href="{event_url}">{html_lib.escape(event_title)}</a></p>'
    )

    sent = sum(
        send_email(to=addr, subject=subject, text=text, html=html)
        for addr in recipients
    )
    logger.info(
        "[email] event-message for event %s: %d/%d delivered.",
        event_id,
        sent,
        len(recipients),
    )
