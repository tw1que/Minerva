from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Order, OrderLine, OrderStatus, StockMovement


OPEN_ORDER_STATUSES = {
    OrderStatus.DRAFT,
    OrderStatus.RESERVED,
    OrderStatus.ALLOCATED,
}


def get_on_hand_qty(db: Session, item_id: int) -> Decimal:
    stmt = select(func.coalesce(func.sum(StockMovement.qty_delta), 0)).where(
        StockMovement.item_id == item_id
    )
    value = db.execute(stmt).scalar_one()
    return Decimal(str(value))


def get_reserved_qty(db: Session, item_id: int) -> Decimal:
    stmt = (
        select(func.coalesce(func.sum(OrderLine.qty_allocated), 0))
        .join(Order, Order.id == OrderLine.order_id)
        .where(OrderLine.item_id == item_id, Order.status.in_(OPEN_ORDER_STATUSES))
    )
    value = db.execute(stmt).scalar_one()
    return Decimal(str(value))


def get_available_qty(db: Session, item_id: int) -> Decimal:
    return get_on_hand_qty(db, item_id) - get_reserved_qty(db, item_id)
