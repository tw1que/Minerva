from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.base import ORMBase


class OrderMaterialCreate(BaseModel):
    order_id: str
    item_id: int
    lot_id: int
    qty_used: Decimal
    used_by: str | None = None
    stock_movement_id: int


class OrderMaterialRead(ORMBase):
    id: int
    order_id: str
    item_id: int
    lot_id: int
    qty_used: Decimal
    used_at: datetime
    used_by: str | None
    stock_movement_id: int
