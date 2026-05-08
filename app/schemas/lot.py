from __future__ import annotations

from datetime import datetime

from app.schemas.base import ORMBase


class LotRead(ORMBase):
    id: int
    item_id: int
    manufacturer_id: int | None
    material_class_id: int | None
    shade_id: int | None
    manufacturer_lot_code: str | None
    lot_code: str
    instance_sku: str
    received_at: datetime
    expires_at: datetime | None
    certificate_ref: str | None
    notes: str | None
    item_sku_snapshot: str
    item_name_snapshot: str
    manufacturer_code_snapshot: str | None
    material_class_code_snapshot: str | None
    shade_code_snapshot: str | None
    created_at: datetime
    updated_at: datetime
