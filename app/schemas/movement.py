from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.db.models import StockReason


class MovementCreate(BaseModel):
    item_id: int
    lot_id: int | None = None
    qty_delta: Decimal
    uom: str
    reason: StockReason
    ref_type: str | None = None
    ref_id: str | None = None
    comment: str | None = None


class MovementRead(BaseModel):
    id: int
    created_at: datetime
    item_id: int
    item_sku: str
    template_name: str
    lot_id: int | None
    qty_delta: Decimal
    uom: str
    reason: StockReason
    comment: str | None
