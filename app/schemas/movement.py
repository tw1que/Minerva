from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.db.models import StockReason


class MovementCreate(BaseModel):
    item_id: int
    lot_id: int | None = None
    qty_delta: Decimal
    unit_id: int | None = None
    uom: str | None = None
    movement_reason_code: str | None = None
    reason: StockReason | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    comment: str | None = None


class MovementRead(BaseModel):
    id: int
    created_at: datetime
    item_id: int
    item_product_code: str
    template_name: str | None
    lot_id: int | None
    qty_delta: Decimal
    unit_code_snapshot: str | None
    movement_reason_code_snapshot: str | None
    reason: StockReason | None
    comment: str | None
