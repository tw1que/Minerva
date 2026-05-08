from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.base import ORMBase


class ReceiveStockRequest(BaseModel):
    item_id: int
    quantity: Decimal = Field(gt=0)
    movement_reason_id: int
    manufacturer_lot_code: str
    manufacturer_id: int | None = None
    material_class_id: int | None = None
    shade_id: int | None = None
    lot_code: str | None = None
    to_location_id: int | None = None
    expires_at: datetime | None = None
    certificate_ref: str | None = None
    notes: str | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    moved_by: str | None = None
    created_by: str | None = None
    comment: str | None = None


class AdjustStockRequest(BaseModel):
    item_id: int
    qty_delta: Decimal
    movement_reason_id: int
    comment: str
    lot_id: int | None = None
    from_location_id: int | None = None
    to_location_id: int | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    moved_by: str | None = None
    created_by: str | None = None


class ConsumeStockRequest(BaseModel):
    order_id: int
    item_id: int
    lot_id: int
    quantity: Decimal = Field(gt=0)
    movement_reason_id: int
    used_by: str | None = None
    created_by: str | None = None
    comment: str | None = None
    from_location_id: int | None = None
    ref_type: str | None = "order_material"
    ref_id: str | None = None


class StockMovementRead(ORMBase):
    id: int
    item_id: int
    lot_id: int | None
    qty_delta: Decimal
    unit_id: int
    unit_code_snapshot: str
    movement_reason_id: int
    movement_reason_code_snapshot: str
    from_location_id: int | None
    from_location_code_snapshot: str | None
    to_location_id: int | None
    to_location_code_snapshot: str | None
    ref_type: str | None
    ref_id: str | None
    moved_at: datetime
    created_at: datetime
    moved_by: str | None
    created_by: str | None
    comment: str | None


class StockBalanceRead(BaseModel):
    key_id: int
    qty_on_hand: Decimal
