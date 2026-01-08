from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import ORMBase


class ManufacturerCreate(BaseModel):
    name: str
    code: str


class ManufacturerRead(ORMBase):
    id: int
    name: str
    code: str
    active: bool
    created_at: datetime
    updated_at: datetime
