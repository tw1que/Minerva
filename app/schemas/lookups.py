from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.db.models import MovementReasonSign
from app.schemas.base import ORMBase


NonEmptyLookupText = Annotated[str, Field(min_length=1)]


class LookupCreateBase(BaseModel):
    code: NonEmptyLookupText
    name: NonEmptyLookupText

    @field_validator("code", "name")
    @classmethod
    def validate_lookup_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty.")
        return normalized


class ManufacturerCreate(LookupCreateBase):
    pass


class ManufacturerRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class ShadeSystemCreate(LookupCreateBase):
    pass


class ShadeSystemRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class ShadeCreate(LookupCreateBase):
    shade_system_id: int


class ShadeRead(ORMBase):
    id: int
    shade_system_id: int
    code: str
    name: str
    active: bool


class MaterialClassCreate(LookupCreateBase):
    pass


class MaterialClassRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class UnitOfMeasureCreate(LookupCreateBase):
    pass


class UnitOfMeasureRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class StockLocationCreate(LookupCreateBase):
    pass


class StockLocationRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool


class MovementReasonCreate(LookupCreateBase):
    allowed_sign: MovementReasonSign


class MovementReasonRead(ORMBase):
    id: int
    code: str
    name: str
    active: bool
    allowed_sign: MovementReasonSign
