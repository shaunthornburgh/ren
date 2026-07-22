from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.crud.order import (
    InsufficientStockError,
    QuantityExceedsMaxError,
    TicketTypeNotFoundError,
)
from app.deps import get_current_active_user, get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderCreate, OrderRead

router = APIRouter(tags=["orders"])


@router.post(
    "/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_in: OrderCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Order:
    """Start a purchase: reserve inventory and create a PENDING order.

    Tickets are issued only once payment succeeds. Follow up with
    ``POST /payments/orders/{order_id}/checkout-session`` to pay.
    """
    try:
        return crud.order.create(db, obj_in=order_in, user_id=current_user.id)
    except TicketTypeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    except QuantityExceedsMaxError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )


@router.get("/my-orders", response_model=list[OrderRead])
def list_my_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Order]:
    """List the authenticated user's orders, newest first."""
    return list(
        crud.order.get_multi_by_user(
            db, user_id=current_user.id, skip=skip, limit=limit
        )
    )
