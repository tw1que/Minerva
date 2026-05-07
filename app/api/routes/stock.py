from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.core.config import settings
from app.db.models import Item, ItemTemplate, Lot, StockMovement, StockReason, UserRole
from app.schemas.movement import MovementCreate, MovementRead
from app.schemas.pagination import Page
from app.services.inventory import (
    AdjustStockCommand,
    InsufficientStockError,
    InventoryError,
    LookupNotFoundError,
    adjust_stock,
    get_available_qty,
)

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

    if payload.qty_delta == 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be zero.")

    if settings.medical_traceability:
        if payload.lot_id is None:
            raise HTTPException(
                status_code=400,
                detail="Medical traceability requires a lot for each movement.",
            )
        if abs(payload.qty_delta) != Decimal("1"):
            raise HTTPException(
                status_code=400,
                detail="Medical traceability requires movement quantity of 1 per item.",
            )
        if not item.track_lots:
            raise HTTPException(
                status_code=400,
                detail="Medical traceability requires items to track lots.",
            )

    reason_code = payload.movement_reason_code or (payload.reason.name if payload.reason else "ADJUST")
    if reason_code == StockReason.ADJUST.name and not payload.comment:
        raise HTTPException(status_code=400, detail="Adjustment requires a comment.")

    try:
        movement = adjust_stock(
            db,
            AdjustStockCommand(
                item_id=payload.item_id,
                lot_id=payload.lot_id,
                quantity_delta=payload.qty_delta,
                unit_id=payload.unit_id,
                movement_reason_code=reason_code,
                ref_type=payload.ref_type,
                ref_id=payload.ref_id,
                comment=payload.comment,
            ),
        )
    except LookupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InventoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MovementRead(
        id=movement.id,
        created_at=movement.created_at,
        item_id=item.id,
        item_product_code=item.sku,
        template_name=item.template.name if item.template else None,
        lot_id=movement.lot_id,
        qty_delta=movement.qty_delta,
        unit_code_snapshot=movement.unit_code_snapshot,
        movement_reason_code_snapshot=movement.movement_reason_code_snapshot,
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
            Item.product_code.label("item_product_code"),
            ItemTemplate.name.label("template_name"),
        )
        .join(Item, StockMovement.item_id == Item.id)
        .outerjoin(ItemTemplate, Item.template_id == ItemTemplate.id)
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
        stmt = stmt.where(
            or_(
                StockMovement.reason == reason,
                StockMovement.movement_reason_code_snapshot == reason.name,
            )
        )

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    rows = (
        db.execute(stmt.order_by(StockMovement.created_at.desc()).offset(offset).limit(page_size))
        .all()
    )

    items: list[MovementRead] = []
    for movement, item_product_code, template_name in rows:
        items.append(
            MovementRead(
                id=movement.id,
                created_at=movement.created_at,
                item_id=movement.item_id,
                item_product_code=item_product_code,
                template_name=template_name,
                lot_id=movement.lot_id,
                qty_delta=movement.qty_delta,
                unit_code_snapshot=movement.unit_code_snapshot,
                movement_reason_code_snapshot=movement.movement_reason_code_snapshot,
                reason=movement.reason,
                comment=movement.comment,
            )
        )

    return {"items": items, "page": page, "page_size": page_size, "total": total}
