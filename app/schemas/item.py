from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.base import ORMBase


class ItemCreate(BaseModel):
    template_id: int
    uom: str
    attributes: dict[str, Any]
    track_lots: bool = True


class ItemVariantCreate(BaseModel):
    uom: str
    attributes: dict[str, Any]
    track_lots: bool = True


class ItemRead(ORMBase):
    id: int
    template_id: int
    product_code: str
    uom: str
    attributes: dict[str, Any]
    attribute_hash: str
    sku_rule_version: int | None
    track_lots: bool
    active: bool
    created_at: datetime
    updated_at: datetime
