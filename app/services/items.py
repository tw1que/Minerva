from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Item, ItemBlank, ItemIvobaseCartridge, Manufacturer, MaterialClass, Shade, UnitOfMeasure


class ItemValidationError(ValueError):
    pass


@dataclass(slots=True)
class CreateItemInput:
    sku: str
    name: str
    item_type: str
    unit_id: int
    manufacturer_id: int | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    active: bool = True


@dataclass(slots=True)
class CreateBlankItemInput(CreateItemInput):
    diameter_mm: Decimal = Decimal("0")
    thickness_mm: Decimal = Decimal("0")
    material_class_id: int = 0
    shade_id: int | None = None
    is_multilayer: bool = False


@dataclass(slots=True)
class CreateIvobaseCartridgeItemInput(CreateItemInput):
    material_class_id: int = 0
    shade_id: int | None = None
    size_code: str = ""


def create_item(db: Session, payload: CreateItemInput) -> Item:
    if not payload.sku.strip() or not payload.name.strip() or not payload.item_type.strip():
        raise ItemValidationError("sku, name, item_type, and unit_id are required.")
    if db.execute(select(Item).where(Item.sku == payload.sku)).scalar_one_or_none():
        raise ItemValidationError("Item SKU already exists.")

    unit = db.get(UnitOfMeasure, payload.unit_id)
    if not unit:
        raise ItemValidationError("Unit not found.")
    if payload.manufacturer_id is not None and not db.get(Manufacturer, payload.manufacturer_id):
        raise ItemValidationError("Manufacturer not found.")

    item = Item(
        sku=payload.sku.strip(),
        name=payload.name.strip(),
        item_type=payload.item_type.strip(),
        manufacturer_id=payload.manufacturer_id,
        unit_id=payload.unit_id,
        metadata_json=payload.metadata_json or {},
        active=payload.active,
    )
    db.add(item)
    db.flush()
    return item


def create_blank_item(db: Session, payload: CreateBlankItemInput) -> Item:
    if payload.item_type.strip().lower() != "blank":
        raise ItemValidationError("Blank items must use item_type='blank'.")
    if payload.diameter_mm <= 0 or payload.thickness_mm <= 0:
        raise ItemValidationError("Blank dimensions must be positive.")
    if not db.get(MaterialClass, payload.material_class_id):
        raise ItemValidationError("Material class not found.")
    if payload.shade_id is not None and not db.get(Shade, payload.shade_id):
        raise ItemValidationError("Shade not found.")

    item = create_item(db, payload)
    db.add(
        ItemBlank(
            item_id=item.id,
            diameter_mm=payload.diameter_mm,
            thickness_mm=payload.thickness_mm,
            material_class_id=payload.material_class_id,
            shade_id=payload.shade_id,
            is_multilayer=payload.is_multilayer,
        )
    )
    db.commit()
    db.refresh(item)
    return item


def create_ivobase_cartridge_item(db: Session, payload: CreateIvobaseCartridgeItemInput) -> Item:
    if payload.item_type.strip().lower() != "ivobase_cartridge":
        raise ItemValidationError("Ivobase cartridge items must use item_type='ivobase_cartridge'.")
    if not payload.size_code.strip():
        raise ItemValidationError("size_code is required.")
    if not db.get(MaterialClass, payload.material_class_id):
        raise ItemValidationError("Material class not found.")
    if payload.shade_id is not None and not db.get(Shade, payload.shade_id):
        raise ItemValidationError("Shade not found.")

    item = create_item(db, payload)
    db.add(
        ItemIvobaseCartridge(
            item_id=item.id,
            material_class_id=payload.material_class_id,
            shade_id=payload.shade_id,
            size_code=payload.size_code.strip(),
        )
    )
    db.commit()
    db.refresh(item)
    return item
