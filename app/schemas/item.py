from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.base import ORMBase


class ItemCreate(BaseModel):
    sku: str
    name: str
    item_type: str
    unit_id: int
    manufacturer_id: int | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class BlankItemCreate(ItemCreate):
    diameter_mm: Decimal = Field(gt=0)
    thickness_mm: Decimal = Field(gt=0)
    material_class_id: int
    shade_id: int | None = None
    is_multilayer: bool = False


class IvobaseCartridgeItemCreate(ItemCreate):
    material_class_id: int
    shade_id: int | None = None
    size_code: str


class ItemBlankRead(ORMBase):
    item_id: int
    diameter_mm: Decimal
    thickness_mm: Decimal
    shade_id: int | None
    material_class_id: int
    is_multilayer: bool


class ItemIvobaseCartridgeRead(ORMBase):
    item_id: int
    shade_id: int | None
    material_class_id: int
    size_code: str


class ItemRead(ORMBase):
    id: int
    item_type: str
    sku: str
    name: str
    manufacturer_id: int | None
    unit_id: int
    active: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    blank_details: ItemBlankRead | None = None
    ivobase_cartridge_details: ItemIvobaseCartridgeRead | None = None
