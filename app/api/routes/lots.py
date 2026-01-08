from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Item, Lot
from app.schemas.lot import LotCreate, LotRead

router = APIRouter(prefix="/lots")


@router.post("/", response_model=LotRead, status_code=status.HTTP_201_CREATED)
def create_lot(
    payload: LotCreate,
    db: Session = Depends(get_db),
) -> Lot:
    item = db.get(Item, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    lot = Lot(
        item_id=payload.item_id,
        lot_code=payload.lot_code,
        supplier_name=payload.supplier_name,
        manufacturing_date=payload.manufacturing_date,
        expires_at=payload.expires_at,
        certificate_ref=payload.certificate_ref,
        notes=payload.notes,
    )

    try:
        db.add(lot)
        db.commit()
        db.refresh(lot)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Lot already exists or violates constraints.",
        ) from exc

    return lot


@router.get("/", response_model=list[LotRead])
def list_lots(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[Lot]:
    stmt = select(Lot).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/{lot_id}", response_model=LotRead)
def get_lot(
    lot_id: int,
    db: Session = Depends(get_db),
) -> Lot:
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found.")
    return lot
