from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.db.models import StockReason
from app.schemas.base import ORMBase


class StockMovementCreate(BaseModel):
    item_id: int
    lot_id: int | None = None
    qty_delta: Decimal
    unit_id: int | None = None
    uom: str | None = None
    movement_reason_code: str | None = None
    reason: StockReason | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    created_by: str | None = None
    comment: str | None = None


class StockMovementRead(ORMBase):
    id: int
    created_at: datetime
    item_id: int
    lot_id: int | None
    qty_delta: Decimal
    unit_id: int | None
    unit_code_snapshot: str | None
    movement_reason_id: int | None
    movement_reason_code_snapshot: str | None
    reason: StockReason | None
    ref_type: str | None
    ref_id: str | None
    created_by: str | None
    comment: str | None
