from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CatalogItemRead(BaseModel):
    id: int
    sku: str
    template_id: int
    template_name: str
    manufacturer_id: int | None
    manufacturer_name: str | None
    uom: str
    attributes: dict[str, Any]
    track_lots: bool
