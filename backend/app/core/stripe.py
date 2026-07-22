"""Thin wrapper around the Stripe SDK.

Keeps all direct Stripe calls in one place so routers/CRUD stay free of SDK
details, and centralises configuration (API key, currency, redirect URLs).
"""

import stripe

from app.core.config import settings
from app.models.order import Order

# Configure the SDK once at import time. In test mode this is a `sk_test_...`
# key; it is read from the environment and never committed.
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeNotConfiguredError(RuntimeError):
    """Raised when a Stripe operation is attempted without keys configured."""


def _to_minor_units(amount: float) -> int:
    """Convert a major-unit price (e.g. 12.50) to Stripe minor units (1250)."""
    # Prices are Decimal off the ORM; scale then round to the nearest cent.
    return int(round(float(amount) * 100))


def create_checkout_session(order: Order) -> stripe.checkout.Session:
    """Create a Stripe Checkout Session for a pending order.

    Builds one line item per order line from the price snapshot taken at
    purchase time, and stamps ``order_id`` into the session metadata (and the
    resulting PaymentIntent) so the webhook can correlate events back to the
    order.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise StripeNotConfiguredError("STRIPE_SECRET_KEY is not configured.")

    line_items = [
        {
            "price_data": {
                "currency": settings.STRIPE_CURRENCY,
                "product_data": {"name": item.ticket_type.name},
                "unit_amount": _to_minor_units(item.unit_price),
            },
            "quantity": item.quantity,
        }
        for item in order.items
    ]

    return stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=(
            f"{settings.FRONTEND_URL}/orders/{order.id}"
            "?status=success&session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=(
            f"{settings.FRONTEND_URL}/orders/{order.id}?status=cancelled"
        ),
        client_reference_id=str(order.id),
        metadata={"order_id": str(order.id)},
        payment_intent_data={"metadata": {"order_id": str(order.id)}},
    )


def construct_event(payload: bytes, sig_header: str | None) -> stripe.Event:
    """Verify a webhook payload's signature and return the parsed event.

    Raises ``ValueError`` for a malformed payload/missing signature and
    ``stripe.error.SignatureVerificationError`` if the signature doesn't match
    the configured signing secret — both should surface as HTTP 400.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise StripeNotConfiguredError(
            "STRIPE_WEBHOOK_SECRET is not configured."
        )
    if not sig_header:
        raise ValueError("Missing Stripe-Signature header.")
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
