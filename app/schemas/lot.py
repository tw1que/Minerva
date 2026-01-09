from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import ORMBase


class LotCreate(BaseModel):
    item_id: int
    lot_code: str
    supplier_name: str | None = None
    manufacturing_date: datetime | None = None
    expires_at: datetime | None = None
    certificate_ref: str | None = None
    notes: str | None = None


class LotRead(ORMBase):
    id: int
    item_id: int
    lot_code: str
    seq: int
    instance_sku: str
    supplier_name: str | None
    manufacturing_date: datetime | None
    received_at: datetime
    expires_at: datetime | None
    certificate_ref: str | None
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
