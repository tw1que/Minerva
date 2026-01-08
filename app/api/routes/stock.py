from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.db.models import Item, ItemTemplate, Lot, StockMovement, StockReason, UserRole
from app.schemas.movement import MovementCreate, MovementRead
from app.schemas.pagination import Page
from app.services.inventory import get_available_qty

router = APIRouter(prefix="/movements")


@router.post("/", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def create_movement(
    payload: MovementCreate,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> MovementRead:
    item = db.get(Item, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    if payload.lot_id is not None:
        lot = db.get(Lot, payload.lot_id)
        if not lot or lot.item_id != item.id:
            raise HTTPException(status_code=404, detail="Lot not found for item.")

    if payload.qty_delta == 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be zero.")

    if payload.reason == StockReason.ADJUST and not payload.comment:
        raise HTTPException(status_code=400, detail="Adjustment requires a comment.")

    if payload.qty_delta < 0:
        available = get_available_qty(db, item.id)
        if available + payload.qty_delta < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough available stock. Available: {available}",
            )

    movement = StockMovement(
        item_id=payload.item_id,
        lot_id=payload.lot_id,
        qty_delta=payload.qty_delta,
        uom=payload.uom,
        reason=payload.reason,
        ref_type=payload.ref_type,
        ref_id=payload.ref_id,
        comment=payload.comment,
    )

    try:
        db.add(movement)
        db.commit()
        db.refresh(movement)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid stock movement.") from exc

    return MovementRead(
        id=movement.id,
        created_at=movement.created_at,
        item_id=item.id,
        item_sku=item.sku,
        template_name=item.template.name,
        lot_id=movement.lot_id,
        qty_delta=movement.qty_delta,
        uom=movement.uom,
        reason=movement.reason,
        comment=movement.comment,
    )


@router.get("/", response_model=Page[MovementRead])
def list_movements(
    search: str | None = None,
    item_id: int | None = None,
    lot_id: int | None = None,
    reason: StockReason | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(
            StockMovement,
            Item.sku.label("item_sku"),
            ItemTemplate.name.label("template_name"),
        )
        .join(Item, StockMovement.item_id == Item.id)
        .join(ItemTemplate, Item.template_id == ItemTemplate.id)
    )

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Item.sku.ilike(pattern), ItemTemplate.name.ilike(pattern))
        )

    if item_id:
        stmt = stmt.where(StockMovement.item_id == item_id)

    if lot_id:
        stmt = stmt.where(StockMovement.lot_id == lot_id)

    if reason:
        stmt = stmt.where(StockMovement.reason == reason)

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    rows = (
        db.execute(stmt.order_by(StockMovement.created_at.desc()).offset(offset).limit(page_size))
        .all()
    )

    items: list[MovementRead] = []
    for movement, item_sku, template_name in rows:
        items.append(
            MovementRead(
                id=movement.id,
                created_at=movement.created_at,
                item_id=movement.item_id,
                item_sku=item_sku,
                template_name=template_name,
                lot_id=movement.lot_id,
                qty_delta=movement.qty_delta,
                uom=movement.uom,
                reason=movement.reason,
                comment=movement.comment,
            )
        )

    return {"items": items, "page": page, "page_size": page_size, "total": total}
