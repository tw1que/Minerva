from __future__ import annotations

from pydantic import BaseModel

from app.db.models import MovementReasonSign
from app.schemas.base import ORMBase


class ManufacturerCreate(BaseModel):
    code: str
    name: str


class ManufacturerRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class ShadeSystemCreate(BaseModel):
    code: str
    name: str


class ShadeSystemRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class ShadeCreate(BaseModel):
    shade_system_id: int
    code: str
    name: str


class ShadeRead(ORMBase):
    id: int
    shade_system_id: int
    code: str
    name: str
    active: bool


class MaterialClassCreate(BaseModel):
    code: str
    name: str


class MaterialClassRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class UnitOfMeasureCreate(BaseModel):
    code: str
    name: str


class UnitOfMeasureRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class StockLocationCreate(BaseModel):
    code: str
    name: str


class StockLocationRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class MovementReasonCreate(BaseModel):
    code: str
    name: str
    allowed_sign: MovementReasonSign


class MovementReasonRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool
    allowed_sign: MovementReasonSign
