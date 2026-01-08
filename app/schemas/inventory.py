from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class InventorySummaryRead(BaseModel):
    item_id: int
    sku: str
    template_name: str
    manufacturer_name: str | None
    uom: str
    on_hand: Decimal
    reserved: Decimal
    available: Decimal
    last_movement: datetime | None
