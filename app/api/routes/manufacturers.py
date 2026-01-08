from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.api.pagination import normalize_pagination
from app.db.models import Manufacturer, UserRole
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerRead
from app.schemas.pagination import Page

router = APIRouter(prefix="/manufacturers")


@router.post("/", response_model=ManufacturerRead, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    payload: ManufacturerCreate,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Manufacturer:
    existing = db.execute(
        select(Manufacturer).where(
            (Manufacturer.name == payload.name) | (Manufacturer.code == payload.code)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Manufacturer already exists.")

    manufacturer = Manufacturer(name=payload.name, code=payload.code)
    db.add(manufacturer)
    db.commit()
    db.refresh(manufacturer)
    return manufacturer


@router.get("/", response_model=Page[ManufacturerRead])
def list_manufacturers(
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Manufacturer)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Manufacturer.name.ilike(pattern), Manufacturer.code.ilike(pattern))
        )

    page, page_size, offset = normalize_pagination(page, page_size)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(stmt.order_by(Manufacturer.name).offset(offset).limit(page_size))
        .scalars()
        .all()
    )
    return {"items": list(items), "page": page, "page_size": page_size, "total": total}


@router.get("/{manufacturer_id}", response_model=ManufacturerRead)
def get_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(get_db),
) -> Manufacturer:
    manufacturer = db.get(Manufacturer, manufacturer_id)
    if not manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found.")
    return manufacturer
