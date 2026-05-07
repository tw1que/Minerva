from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.core.config import settings
from app.db.models import Item, Lot, UserRole
from app.schemas.lot import LotCreate, LotRead
from app.schemas.pagination import Page
from app.services.inventory import LookupNotFoundError, create_lot_snapshot

router = APIRouter(prefix="/lots")


@router.post("/", response_model=LotRead, status_code=status.HTTP_201_CREATED)
def create_lot(
    payload: LotCreate,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Lot:
    item = db.get(Item, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    if settings.medical_traceability and not item.track_lots:
        raise HTTPException(
            status_code=400,
            detail="Medical traceability requires items to track lots.",
        )

    try:
        with db.begin():
            lot = create_lot_snapshot(
                db,
                item=item,
                manufacturer_id=payload.manufacturer_id,
                material_class_id=payload.material_class_id,
                shade_id=payload.shade_id,
                manufacturer_lot_code=payload.manufacturer_lot_code or payload.lot_code,
                supplier_name=payload.supplier_name,
                manufacturing_date=payload.manufacturing_date,
                expires_at=payload.expires_at,
                certificate_ref=payload.certificate_ref,
                notes=payload.notes,
            )
        db.refresh(lot)
    except LookupNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return lot


@router.get("/", response_model=Page[LotRead])
def list_lots(
    item_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Lot)
    if item_id:
        stmt = stmt.where(Lot.item_id == item_id)

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(stmt.order_by(Lot.received_at.desc()).offset(offset).limit(page_size))
        .scalars()
        .all()
    )
    return {"items": list(items), "page": page, "page_size": page_size, "total": total}


@router.get("/{lot_id}", response_model=LotRead)
def get_lot(
    lot_id: int,
    db: Session = Depends(get_db),
) -> Lot:
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found.")
    return lot
