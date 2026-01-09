from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import AttributeType
from app.schemas.base import ORMBase


class AllowedRange(BaseModel):
    min: int | float | str | None = None
    max: int | float | str | None = None
    step: int | float | str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "AllowedRange":
        def _to_decimal(value: int | float | str) -> Decimal:
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ValueError("allowed_range values must be numeric.") from exc

        if self.min is not None and self.max is not None:
            if _to_decimal(self.min) > _to_decimal(self.max):
                raise ValueError("allowed_range min must be <= max.")
        if self.step is not None and _to_decimal(self.step) <= 0:
            raise ValueError("allowed_range step must be > 0.")
        return self


class AttributeSpec(BaseModel):
    key: str
    type: AttributeType
    required: bool = False
    allowed_values: list[Any] | None = None
    allowed_range: AllowedRange | None = None
    unit: str | None = None
    normalize: dict[str, Any] | list[str] | str | None = None
    sku_pad: int | dict[str, Any] | None = None
    sku_map: dict[str, str] | None = None
    include_in_identity: bool = True
    include_in_sku: bool = True

    @field_validator("sku_pad")
    @classmethod
    def validate_sku_pad(cls, value: int | dict[str, Any] | None) -> int | dict[str, Any] | None:
        if value is None:
            return value
        if isinstance(value, int):
            if value <= 0:
                raise ValueError("sku_pad width must be > 0.")
            return value
        if isinstance(value, dict):
            width = value.get("width")
            char = value.get("char", "0")
            if not isinstance(width, int) or width <= 0:
                raise ValueError("sku_pad width must be > 0.")
            if not isinstance(char, str) or len(char) != 1:
                raise ValueError("sku_pad char must be a single character.")
            return value
        raise ValueError("sku_pad must be an integer or object.")

    @model_validator(mode="after")
    def validate_allowed(self) -> "AttributeSpec":
        if self.allowed_values is not None and self.allowed_range is not None:
            raise ValueError("Provide only allowed_values or allowed_range.")
        if self.type == AttributeType.ENUM and not self.allowed_values:
            raise ValueError("Enum attributes require allowed_values.")
        return self


class SKURule(BaseModel):
    prefix: str
    separator: str = "-"
    tokens: list[str] = Field(default_factory=list)
    token_format: dict[str, dict[str, Any]] | None = None
    version: int = 1
    freeze_existing_skus: bool = True

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("SKU prefix cannot be empty.")
        return value

    @field_validator("tokens")
    @classmethod
    def validate_tokens(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("SKU tokens must be unique.")
        return value


class TemplateCreate(BaseModel):
    name: str
    manufacturer_id: int | None = None
    attribute_specs: list[AttributeSpec] = Field(default_factory=list)
    sku_rule: SKURule

    @model_validator(mode="after")
    def validate_specs_and_tokens(self) -> "TemplateCreate":
        keys = [spec.key for spec in self.attribute_specs]
        if len(set(keys)) != len(keys):
            raise ValueError("Attribute spec keys must be unique.")
        missing = [token for token in self.sku_rule.tokens if token not in set(keys)]
        if missing:
            raise ValueError(f"SKU tokens missing from attribute specs: {', '.join(missing)}.")
        return self


class TemplateRead(ORMBase):
    id: int
    name: str
    manufacturer_id: int | None
    attribute_specs: list[AttributeSpec] = Field(default_factory=list)
    sku_rule: SKURule
    active: bool
    created_at: datetime
    updated_at: datetime
