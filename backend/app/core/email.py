"""Minimal transactional email helper.

Sends via SMTP when configured; otherwise falls back to a "console backend"
that logs the message (handy for local dev). Nothing here raises to callers —
email is best-effort and must never break the request that triggered it.
"""

import html as html_lib
import io
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from email.message import EmailMessage
from email.utils import make_msgid
from zoneinfo import ZoneInfo

import segno

from app.core.config import settings

# Email readers' zones are unknown; the site's audience is UK-based.
EMAIL_TZ = ZoneInfo("Europe/London")

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


@dataclass
class ConfirmationTicket:
    type_name: str
    code: str


@dataclass
class ConfirmationEvent:
    event_id: int
    title: str
    start: datetime
    end: datetime
    location: str | None
    is_online: bool
    tickets: list[ConfirmationTicket]


@dataclass
class OrderConfirmationEmail:
    """Everything needed to email a buyer their tickets once an order is paid.

    Plain data (no ORM objects) so it can be handed to a background task.
    """

    order_id: int
    to: str
    buyer_name: str | None
    total_amount: Decimal
    events: list[ConfirmationEvent]


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


def _format_code(code: str) -> str:
    """Group a ticket code in fours (``7K3Q-X9MZ-2B4H``), like the frontend."""
    return "-".join(code[i : i + 4] for i in range(0, len(code), 4))


def _format_when(start: datetime, end: datetime) -> str:
    """Event time range in UK local time, e.g. ``Sat 10 Jan 2027, 18:00 GMT``."""
    start_local = start.astimezone(EMAIL_TZ)
    end_local = end.astimezone(EMAIL_TZ)
    fmt = "%a %d %b %Y, %H:%M"
    if end_local.date() == start_local.date():
        return f"{start_local.strftime(fmt)}-{end_local.strftime('%H:%M %Z')}"
    return f"{start_local.strftime(fmt + ' %Z')} to {end_local.strftime(fmt + ' %Z')}"


def _format_where(event: ConfirmationEvent) -> str:
    if not event.location:
        return "Venue TBA"
    return f"Online: {event.location}" if event.is_online else event.location


def _qr_png(code: str) -> bytes:
    """A scannable PNG QR code encoding the raw ticket code.

    ``make_qr`` forces a standard QR code; ``segno.make`` would pick a Micro QR
    for short codes, which phone cameras and the door scanner can't read.
    """
    buffer = io.BytesIO()
    segno.make_qr(code, error="m").save(
        buffer, kind="png", scale=6, dark="#111827", light="#ffffff"
    )
    return buffer.getvalue()


def _confirmation_subject(data: OrderConfirmationEmail) -> str:
    """Subject line. Whitespace runs in the title collapse to single spaces,
    since a header can't carry line breaks."""
    if len(data.events) == 1:
        title = " ".join(data.events[0].title.split())
        return f"Your tickets for {title}"
    return f"Your tickets for order #{data.order_id}"


def build_order_confirmation(data: OrderConfirmationEmail) -> EmailMessage:
    """Compose the order confirmation: text part, HTML part, inline QR PNGs."""
    esc = html_lib.escape
    total = f"{data.total_amount:.2f} {settings.STRIPE_CURRENCY.upper()}"
    my_tickets_url = f"{settings.FRONTEND_URL}/my-tickets"
    greeting = f"Hi {data.buyer_name}," if data.buyer_name else "Hi,"

    text_lines = [
        greeting,
        "",
        f"Your order #{data.order_id} is confirmed. Total paid: {total}.",
    ]
    html_parts = [
        f"<p>{esc(greeting)}</p>",
        f"<p>Your order <strong>#{data.order_id}</strong> is confirmed. "
        f"Total paid: <strong>{esc(total)}</strong>.</p>",
    ]
    images: list[tuple[str, bytes]] = []

    for event in data.events:
        when = _format_when(event.start, event.end)
        where = _format_where(event)
        event_url = f"{settings.FRONTEND_URL}/events/{event.event_id}"
        text_lines += ["", event.title, f"When: {when}", f"Where: {where}", event_url]
        html_parts.append(
            '<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">'
            f'<h2 style="margin:0 0 8px">{esc(event.title)}</h2>'
            f'<p style="color:#6b7280;margin:0">When: {esc(when)}</p>'
            f'<p style="color:#6b7280;margin:0 0 8px">Where: {esc(where)}</p>'
            f'<p style="margin:0 0 16px"><a href="{event_url}">View event</a></p>'
        )
        for ticket in event.tickets:
            code = _format_code(ticket.code)
            cid = make_msgid(domain="ren.local")
            images.append((cid, _qr_png(ticket.code)))
            text_lines.append(f"- {ticket.type_name}: {code}")
            html_parts.append(
                '<div style="margin:0 0 20px">'
                f'<p style="margin:0 0 6px;font-weight:600">{esc(ticket.type_name)}</p>'
                f'<img src="cid:{cid[1:-1]}" width="200" height="200" '
                f'alt="QR code for ticket {code}" style="display:block">'
                f'<p style="margin:6px 0 0;font-family:monospace;font-size:16px">{code}</p>'
                "</div>"
            )

    text_lines += [
        "",
        "Show the QR code at the door.",
        f"Your tickets: {my_tickets_url}",
    ]
    html_parts.append(
        '<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">'
        "<p>Show the QR code at the door.</p>"
        f'<p><a href="{my_tickets_url}" '
        'style="display:inline-block;padding:10px 18px;background:#7c3aed;'
        'color:#fff;border-radius:9999px;text-decoration:none">My tickets</a></p>'
    )

    msg = EmailMessage()
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = data.to
    msg["Subject"] = _confirmation_subject(data)
    msg.set_content("\n".join(text_lines) + "\n")
    msg.add_alternative("".join(html_parts), subtype="html")
    html_part = msg.get_payload()[1]
    for cid, png in images:
        html_part.add_related(png, maintype="image", subtype="png", cid=cid)
    return msg


def send_order_confirmation(data: OrderConfirmationEmail) -> None:
    """Email the buyer their tickets. Designed to run in a background task.

    Never raises: a failure to build or send is logged and dropped.
    """
    try:
        msg = build_order_confirmation(data)
    except Exception:  # noqa: BLE001 - best-effort; log and move on.
        logger.exception("[email] Could not build confirmation for order %s", data.order_id)
        return
    sent = _deliver(msg)
    logger.info(
        "[email] order-confirmation for order %s: %s.",
        data.order_id,
        "delivered" if sent else "failed",
    )
