from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Item, Lot, StockMovement
from app.schemas.stock import StockMovementCreate, StockMovementRead

router = APIRouter(prefix="/stock")


@router.post("/movements", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def create_stock_movement(
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
) -> StockMovement:
    item = db.get(Item, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    if payload.lot_id is not None:
        lot = db.get(Lot, payload.lot_id)
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found.")

    movement = StockMovement(
        item_id=payload.item_id,
        lot_id=payload.lot_id,
        qty_delta=payload.qty_delta,
        uom=payload.uom,
        reason=payload.reason,
        ref_type=payload.ref_type,
        ref_id=payload.ref_id,
        created_by=payload.created_by,
        comment=payload.comment,
    )

    try:
        db.add(movement)
        db.commit()
        db.refresh(movement)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid stock movement.") from exc
    return movement


@router.get("/movements", response_model=list[StockMovementRead])
def list_stock_movements(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[StockMovement]:
    stmt = select(StockMovement).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/movements/{movement_id}", response_model=StockMovementRead)
def get_stock_movement(
    movement_id: int,
    db: Session = Depends(get_db),
) -> StockMovement:
    movement = db.get(StockMovement, movement_id)
    if not movement:
        raise HTTPException(status_code=404, detail="Stock movement not found.")
    return movement
