from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db, require_roles
from app.db.models import Item, User, UserRole
from app.schemas.item import BlankItemCreate, ItemCreate, ItemRead, IvobaseCartridgeItemCreate
from app.services.items import (
    CreateBlankItemInput,
    CreateItemInput,
    CreateIvobaseCartridgeItemInput,
    ItemValidationError,
    create_blank_item,
    create_item,
    create_ivobase_cartridge_item,
)

router = APIRouter(prefix="/items")


@router.get("", response_model=list[ItemRead])
def list_items(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    return list(
        db.execute(
            select(Item)
            .options(selectinload(Item.blank_details), selectinload(Item.ivobase_cartridge_details))
            .order_by(Item.id)
        ).scalars()
    )


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_generic_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        return create_item(
            db,
            CreateItemInput(
                sku=payload.sku,
                name=payload.name,
                item_type=payload.item_type,
                unit_id=payload.unit_id,
                manufacturer_id=payload.manufacturer_id,
                metadata_json=payload.metadata_json,
            ),
        )
    except ItemValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
):
    item = db.execute(
        select(Item)
        .options(selectinload(Item.blank_details), selectinload(Item.ivobase_cartridge_details))
        .where(Item.id == item_id)
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    return item


@router.post("/blanks", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_blank(
    payload: BlankItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        return create_blank_item(
            db,
            CreateBlankItemInput(
                sku=payload.sku,
                name=payload.name,
                item_type=payload.item_type,
                unit_id=payload.unit_id,
                manufacturer_id=payload.manufacturer_id,
                metadata_json=payload.metadata_json,
                diameter_mm=payload.diameter_mm,
                thickness_mm=payload.thickness_mm,
                material_class_id=payload.material_class_id,
                shade_id=payload.shade_id,
                is_multilayer=payload.is_multilayer,
            ),
        )
    except ItemValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ivobase-cartridges", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_ivobase_cartridge(
    payload: IvobaseCartridgeItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        return create_ivobase_cartridge_item(
            db,
            CreateIvobaseCartridgeItemInput(
                sku=payload.sku,
                name=payload.name,
                item_type=payload.item_type,
                unit_id=payload.unit_id,
                manufacturer_id=payload.manufacturer_id,
                metadata_json=payload.metadata_json,
                material_class_id=payload.material_class_id,
                shade_id=payload.shade_id,
                size_code=payload.size_code,
            ),
        )
    except ItemValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
