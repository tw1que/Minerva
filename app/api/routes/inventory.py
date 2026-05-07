from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.pagination import normalize_pagination
from app.db.models import Item, ItemTemplate, Manufacturer, Order, OrderLine, OrderStatus, StockMovement
from app.schemas.inventory import InventorySummaryRead
from app.schemas.pagination import Page

router = APIRouter(prefix="/inventory")


@router.get("/summary", response_model=Page[InventorySummaryRead])
def inventory_summary(
    search: str | None = None,
    manufacturer_id: int | None = None,
    attr_key: str | None = None,
    attr_val: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
) -> dict:
    movement_subq = (
        select(
            StockMovement.item_id.label("item_id"),
            func.coalesce(func.sum(StockMovement.qty_delta), 0).label("on_hand"),
            func.max(StockMovement.created_at).label("last_movement"),
        )
        .group_by(StockMovement.item_id)
        .subquery()
    )

    reserved_subq = (
        select(
            OrderLine.item_id.label("item_id"),
            func.coalesce(func.sum(OrderLine.qty_allocated), 0).label("reserved"),
        )
        .join(Order, Order.id == OrderLine.order_id)
        .where(Order.status.in_([OrderStatus.DRAFT, OrderStatus.RESERVED, OrderStatus.ALLOCATED]))
        .group_by(OrderLine.item_id)
        .subquery()
    )

    stmt = (
        select(
            Item.id.label("item_id"),
            Item.sku.label("product_code"),
            Item.uom,
            ItemTemplate.name.label("template_name"),
            Manufacturer.name.label("manufacturer_name"),
            movement_subq.c.on_hand,
            movement_subq.c.last_movement,
            reserved_subq.c.reserved,
        )
        .outerjoin(ItemTemplate, Item.template_id == ItemTemplate.id)
        .outerjoin(Manufacturer, Item.manufacturer_id == Manufacturer.id)
        .outerjoin(movement_subq, movement_subq.c.item_id == Item.id)
        .outerjoin(reserved_subq, reserved_subq.c.item_id == Item.id)
    )

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Item.sku.ilike(pattern),
                ItemTemplate.name.ilike(pattern),
                Manufacturer.name.ilike(pattern),
            )
        )

    if manufacturer_id:
        stmt = stmt.where(Item.manufacturer_id == manufacturer_id)

    if attr_key and attr_val:
        stmt = stmt.where(Item.attributes[attr_key].astext.ilike(f"%{attr_val}%"))

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    rows = (
        db.execute(stmt.order_by(Item.sku).offset(offset).limit(page_size)).all()
    )

    items: list[InventorySummaryRead] = []
    for row in rows:
        on_hand = Decimal(str(row.on_hand or 0))
        reserved = Decimal(str(row.reserved or 0))
        items.append(
            InventorySummaryRead(
                item_id=row.item_id,
                product_code=row.product_code,
                template_name=row.template_name or row.product_code,
                manufacturer_name=row.manufacturer_name,
                uom=row.uom,
                on_hand=on_hand,
                reserved=reserved,
                available=on_hand - reserved,
                last_movement=row.last_movement,
            )
        )

    return {"items": items, "page": page, "page_size": page_size, "total": total}
