from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Item, Lot, OrderMaterial, StockMovement
from app.schemas.order import OrderMaterialCreate, OrderMaterialRead

router = APIRouter(prefix="/orders")


@router.post("/materials", response_model=OrderMaterialRead, status_code=status.HTTP_201_CREATED)
def create_order_material(
    payload: OrderMaterialCreate,
    db: Session = Depends(get_db),
) -> OrderMaterial:
    item = db.get(Item, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    lot = db.get(Lot, payload.lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found.")

    movement = db.get(StockMovement, payload.stock_movement_id)
    if not movement:
        raise HTTPException(status_code=404, detail="Stock movement not found.")

    order_material = OrderMaterial(
        order_id=payload.order_id,
        item_id=payload.item_id,
        lot_id=payload.lot_id,
        qty_used=payload.qty_used,
        used_by=payload.used_by,
        stock_movement_id=payload.stock_movement_id,
    )

    try:
        db.add(order_material)
        db.commit()
        db.refresh(order_material)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order material already exists.") from exc
    return order_material


@router.get("/materials", response_model=list[OrderMaterialRead])
def list_order_materials(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[OrderMaterial]:
    stmt = select(OrderMaterial).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/materials/{material_id}", response_model=OrderMaterialRead)
def get_order_material(
    material_id: int,
    db: Session = Depends(get_db),
) -> OrderMaterial:
    material = db.get(OrderMaterial, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Order material not found.")
    return material
