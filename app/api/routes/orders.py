from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.db.models import Item, ItemTemplate, Order, OrderLine, OrderStatus, User, UserRole
from app.schemas.order import (
    OrderAllocate,
    OrderCreate,
    OrderDetailRead,
    OrderLineCreate,
    OrderLineRead,
    OrderListItem,
    OrderRead,
)
from app.schemas.pagination import Page
from app.services.inventory import get_available_qty

router = APIRouter(prefix="/orders")


def _refresh_order_status(db: Session, order: Order) -> None:
    lines = (
        db.execute(select(OrderLine).where(OrderLine.order_id == order.id))
        .scalars()
        .all()
    )
    if not lines:
        order.status = OrderStatus.DRAFT
        return

    if all(line.qty_allocated >= line.qty_requested for line in lines):
        order.status = OrderStatus.ALLOCATED
    elif any(line.qty_allocated > 0 for line in lines):
        order.status = OrderStatus.RESERVED
    else:
        order.status = OrderStatus.DRAFT


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Order:
    if not payload.order_number.strip():
        raise HTTPException(status_code=400, detail="Order number is required.")

    order = Order(
        order_number=payload.order_number.strip(),
        status=OrderStatus.DRAFT,
        notes=payload.notes,
        created_by_id=user.id,
    )

    try:
        db.add(order)
        db.commit()
        db.refresh(order)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order number already exists.") from exc

    return order


@router.get("/", response_model=Page[OrderListItem])
def list_orders(
    search: str | None = None,
    status_filter: OrderStatus | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
) -> dict:
    totals_subq = (
        select(
            OrderLine.order_id.label("order_id"),
            func.count(OrderLine.id).label("line_count"),
            func.coalesce(func.sum(OrderLine.qty_requested), 0).label("qty_requested"),
            func.coalesce(func.sum(OrderLine.qty_allocated), 0).label("qty_allocated"),
        )
        .group_by(OrderLine.order_id)
        .subquery()
    )

    stmt = (
        select(
            Order,
            totals_subq.c.line_count,
            totals_subq.c.qty_requested,
            totals_subq.c.qty_allocated,
        )
        .outerjoin(totals_subq, totals_subq.c.order_id == Order.id)
    )

    if search:
        stmt = stmt.where(Order.order_number.ilike(f"%{search}%"))

    if status_filter:
        stmt = stmt.where(Order.status == status_filter)

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    rows = (
        db.execute(stmt.order_by(Order.created_at.desc()).offset(offset).limit(page_size))
        .all()
    )

    items: list[OrderListItem] = []
    for order, line_count, qty_requested, qty_allocated in rows:
        items.append(
            OrderListItem(
                id=order.id,
                order_number=order.order_number,
                status=order.status,
                notes=order.notes,
                created_at=order.created_at,
                updated_at=order.updated_at,
                line_count=int(line_count or 0),
                qty_requested=Decimal(str(qty_requested or 0)),
                qty_allocated=Decimal(str(qty_allocated or 0)),
            )
        )

    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/{order_id}", response_model=OrderDetailRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
) -> OrderDetailRead:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    lines_stmt = (
        select(
            OrderLine,
            Item.product_code.label("item_product_code"),
            ItemTemplate.name.label("template_name"),
        )
        .join(Item, OrderLine.item_id == Item.id)
        .join(ItemTemplate, Item.template_id == ItemTemplate.id)
        .where(OrderLine.order_id == order_id)
    )

    rows = db.execute(lines_stmt).all()
    lines: list[OrderLineRead] = []
    for line, item_product_code, template_name in rows:
        available = get_available_qty(db, line.item_id)
        lines.append(
            OrderLineRead(
                id=line.id,
                order_id=line.order_id,
                item_id=line.item_id,
                item_product_code=item_product_code,
                template_name=template_name,
                qty_requested=line.qty_requested,
                qty_allocated=line.qty_allocated,
                uom=line.uom,
                available=available,
            )
        )

    return OrderDetailRead(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        lines=lines,
    )


@router.post("/{order_id}/lines", response_model=OrderLineRead, status_code=status.HTTP_201_CREATED)
def add_order_line(
    order_id: int,
    payload: OrderLineCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> OrderLineRead:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.status in {OrderStatus.CANCELLED, OrderStatus.FULFILLED}:
        raise HTTPException(status_code=400, detail="Order is closed.")

    item = db.get(Item, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    existing = db.execute(
        select(OrderLine).where(
            OrderLine.order_id == order_id,
            OrderLine.item_id == item.id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.qty_requested += payload.qty_requested
        line = existing
    else:
        line = OrderLine(
            order_id=order_id,
            item_id=item.id,
            qty_requested=payload.qty_requested,
            uom=item.uom,
        )
        db.add(line)

    _refresh_order_status(db, order)
    db.commit()
    db.refresh(line)

    available = get_available_qty(db, line.item_id)
    return OrderLineRead(
        id=line.id,
        order_id=line.order_id,
        item_id=line.item_id,
        item_product_code=item.product_code,
        template_name=item.template.name,
        qty_requested=line.qty_requested,
        qty_allocated=line.qty_allocated,
        uom=line.uom,
        available=available,
    )


@router.post("/{order_id}/allocate", response_model=OrderLineRead)
def allocate_order(
    order_id: int,
    payload: OrderAllocate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> OrderLineRead:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.status in {OrderStatus.CANCELLED, OrderStatus.FULFILLED}:
        raise HTTPException(status_code=400, detail="Order is closed.")

    line = db.get(OrderLine, payload.line_id)
    if not line or line.order_id != order_id:
        raise HTTPException(status_code=404, detail="Order line not found.")

    remaining = line.qty_requested - line.qty_allocated
    allocate_qty = payload.qty or remaining
    if allocate_qty <= 0:
        raise HTTPException(status_code=400, detail="Allocation must be greater than zero.")
    if allocate_qty > remaining:
        raise HTTPException(status_code=400, detail="Allocation exceeds line quantity.")

    available = get_available_qty(db, line.item_id)
    if allocate_qty > available:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough available stock. Available: {available}",
        )

    line.qty_allocated += allocate_qty
    _refresh_order_status(db, order)
    db.commit()
    db.refresh(line)

    updated_available = get_available_qty(db, line.item_id)
    return OrderLineRead(
        id=line.id,
        order_id=line.order_id,
        item_id=line.item_id,
        item_product_code=line.item.product_code,
        template_name=line.item.template.name,
        qty_requested=line.qty_requested,
        qty_allocated=line.qty_allocated,
        uom=line.uom,
        available=updated_available,
    )


@router.put("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> OrderRead:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
