from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import ORMBase


class ItemBlankDetailsCreate(BaseModel):
    diameter_mm: Decimal = Field(gt=0)
    thickness_mm: Decimal = Field(gt=0)
    material_class_id: int
    shade_id: int | None = None
    is_multilayer: bool = False


class ItemIvobaseCartridgeDetailsCreate(BaseModel):
    material_class_id: int
    size_code: str
    shade_id: int | None = None


class ItemBlankDetailsRead(ORMBase):
    diameter_mm: Decimal
    thickness_mm: Decimal
    material_class_id: int
    shade_id: int | None
    is_multilayer: bool


class ItemIvobaseCartridgeDetailsRead(ORMBase):
    material_class_id: int
    shade_id: int | None
    size_code: str


class ItemCreate(BaseModel):
    template_id: int | None = None
    manufacturer_id: int | None = None
    unit_id: int | None = None
    uom: str | None = None
    item_type: str | None = None
    name: str | None = None
    sku: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    track_lots: bool = True
    blank_details: ItemBlankDetailsCreate | None = None
    ivobase_cartridge_details: ItemIvobaseCartridgeDetailsCreate | None = None


class ItemVariantCreate(BaseModel):
    manufacturer_id: int | None = None
    uom: str
    attributes: dict[str, Any]
    track_lots: bool = True


class ItemRead(ORMBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    item_type: str | None
    template_id: int | None
    manufacturer_id: int | None
    unit_id: int | None
    sku: str
    product_code: str
    name: str | None
    uom: str | None
    attributes: dict[str, Any]
    attribute_hash: str | None
    metadata: dict[str, Any] = Field(alias="metadata_json")
    sku_rule_version: int | None
    track_lots: bool
    active: bool
    created_at: datetime
    updated_at: datetime
    blank_details: ItemBlankDetailsRead | None = None
    ivobase_cartridge_details: ItemIvobaseCartridgeDetailsRead | None = None
