from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import ORMBase


class LotCreate(BaseModel):
    item_id: int
    manufacturer_id: int | None = None
    material_class_id: int | None = None
    shade_id: int | None = None
    lot_code: str
    manufacturer_lot_code: str | None = None
    supplier_name: str | None = None
    manufacturing_date: datetime | None = None
    expires_at: datetime | None = None
    certificate_ref: str | None = None
    notes: str | None = None


class LotRead(ORMBase):
    id: int
    item_id: int
    manufacturer_id: int | None
    material_class_id: int | None
    shade_id: int | None
    lot_code: str
    manufacturer_lot_code: str | None
    seq: int
    instance_sku: str
    supplier_name: str | None
    manufacturing_date: datetime | None
    received_at: datetime
    expires_at: datetime | None
    certificate_ref: str | None
    notes: str | None
    manufacturer_code_snapshot: str | None
    material_class_code_snapshot: str | None
    shade_code_snapshot: str | None
    item_sku_snapshot: str | None
    item_name_snapshot: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
