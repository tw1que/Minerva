from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.db.models import OrderStatus
from app.schemas.base import ORMBase


class OrderCreate(BaseModel):
    order_number: str
    status: OrderStatus = OrderStatus.DRAFT
    notes: str | None = None


class OrderRead(ORMBase):
    id: int
    order_number: str
    status: OrderStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class OrderMaterialRead(ORMBase):
    id: int
    order_id: int
    item_id: int
    lot_id: int
    qty_used: Decimal
    unit_id: int
    unit_code_snapshot: str
    item_sku_snapshot: str
    item_name_snapshot: str
    lot_code_snapshot: str
    material_class_code_snapshot: str | None
    shade_code_snapshot: str | None
    stock_movement_id: int
    used_at: datetime
    used_by: str | None
