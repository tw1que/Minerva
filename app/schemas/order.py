from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.db.models import OrderStatus
from app.schemas.base import ORMBase


class OrderCreate(BaseModel):
    order_number: str
    notes: str | None = None


class OrderListItem(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    line_count: int
    qty_requested: Decimal
    qty_allocated: Decimal


class OrderRead(ORMBase):
    id: int
    order_number: str
    status: OrderStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class OrderLineCreate(BaseModel):
    item_id: int
    qty_requested: Decimal = Field(gt=0)


class OrderLineRead(BaseModel):
    id: int
    order_id: int
    item_id: int
    item_product_code: str
    template_name: str
    qty_requested: Decimal
    qty_allocated: Decimal
    uom: str
    available: Decimal


class OrderDetailRead(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[OrderLineRead] = Field(default_factory=list)


class OrderAllocate(BaseModel):
    line_id: int
    qty: Decimal | None = Field(default=None, gt=0)
