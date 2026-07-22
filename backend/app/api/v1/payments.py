import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import crud
from app.core import stripe as stripe_service
from app.deps import get_current_active_user, get_db
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import CheckoutSessionRead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])


@router.post(
    "/payments/orders/{order_id}/checkout-session",
    response_model=CheckoutSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_checkout_session(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CheckoutSessionRead:
    """Create a Stripe Checkout Session for the caller's pending order."""
    order = crud.order.get(db, id=order_id)
    if order is None or order.user_id != current_user.id:
        # Don't leak the existence of other users' orders.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.status is not OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is {order.status.value}, not awaiting payment.",
        )

    try:
        session = stripe_service.create_checkout_session(order)
    except stripe_service.StripeNotConfiguredError:
        logger.exception("Stripe is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments are not currently available.",
        )
    except stripe.error.StripeError:
        logger.exception("Failed to create Stripe Checkout Session")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create a payment session.",
        )

    order.stripe_session_id = session.id
    db.add(order)
    db.commit()

    return CheckoutSessionRead(checkout_url=session.url, session_id=session.id)


@router.post("/payments/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    """Receive and process Stripe webhook events.

    The signature is verified against the raw request body before anything is
    trusted. Handlers are idempotent so Stripe's at-least-once delivery (and
    retries) can't double-issue tickets or double-release inventory.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe_service.construct_event(payload, sig_header)
    except stripe_service.StripeNotConfiguredError:
        logger.exception("Stripe webhook secret not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook handling is not configured.",
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        # Malformed payload or bad signature — reject without processing.
        logger.warning("Rejected Stripe webhook: invalid signature/payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature.",
        )

    event_type = event["type"]
    obj = event["data"]["object"]
    order_id = _order_id_from(obj)

    if event_type in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        # For synchronous methods (cards) the session is already paid; for
        # asynchronous ones wait for async_payment_succeeded. Guard on
        # payment_status so an unpaid "completed" event doesn't fulfil early.
        if obj.get("payment_status") == "paid" and order_id is not None:
            crud.order.fulfill(
                db,
                order_id=order_id,
                payment_intent_id=obj.get("payment_intent"),
            )
    elif event_type in (
        "checkout.session.expired",
        "checkout.session.async_payment_failed",
    ):
        if order_id is not None:
            crud.order.release(db, order_id=order_id)
    else:
        logger.debug("Ignoring unhandled Stripe event type: %s", event_type)

    # Always 200 for events we accepted so Stripe stops retrying.
    return {"received": True}


def _order_id_from(session_obj: dict) -> int | None:
    """Extract our order id from a Checkout Session's metadata."""
    metadata = session_obj.get("metadata") or {}
    raw = metadata.get("order_id") or session_obj.get("client_reference_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Stripe event carried non-integer order_id: %r", raw)
        return None
