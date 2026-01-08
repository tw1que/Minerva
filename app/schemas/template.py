from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import SKUSequenceScope, TemplateFieldType
from app.schemas.base import ORMBase


class TemplateFieldCreate(BaseModel):
    field_key: str
    field_type: TemplateFieldType
    required: bool = False
    include_in_sku: bool = False
    sku_order: int | None = None
    default_value: str | None = None
    enum_values: dict | None = None
    format: str | None = None


class TemplateCreate(BaseModel):
    name: str
    manufacturer_id: int | None = None
    sku_prefix: str
    sku_pattern: str
    seq_scope: SKUSequenceScope
    fields: list[TemplateFieldCreate] = Field(default_factory=list)


class TemplateFieldRead(ORMBase):
    id: int
    template_id: int
    field_key: str
    field_type: TemplateFieldType
    required: bool
    include_in_sku: bool
    sku_order: int | None
    default_value: str | None
    enum_values: dict | None
    format: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class TemplateRead(ORMBase):
    id: int
    name: str
    manufacturer_id: int | None
    sku_prefix: str
    sku_pattern: str
    seq_scope: SKUSequenceScope
    active: bool
    created_at: datetime
    updated_at: datetime
    fields: list[TemplateFieldRead] = Field(default_factory=list)
