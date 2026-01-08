from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Manufacturer
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerRead

router = APIRouter(prefix="/manufacturers")


@router.post("/", response_model=ManufacturerRead, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    payload: ManufacturerCreate,
    db: Session = Depends(get_db),
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


@router.get("/", response_model=list[ManufacturerRead])
def list_manufacturers(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[Manufacturer]:
    stmt = select(Manufacturer).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/{manufacturer_id}", response_model=ManufacturerRead)
def get_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(get_db),
) -> Manufacturer:
    manufacturer = db.get(Manufacturer, manufacturer_id)
    if not manufacturer:
        raise HTTPException(status_code=404, detail="Manufacturer not found.")
    return manufacturer
