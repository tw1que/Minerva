from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.db.models import TemplateField, TemplateFieldType


class AttributeValidationError(ValueError):
    pass


def _coerce_value(field: TemplateField, value: Any) -> Any:
    if value is None:
        return None

    field_type = field.field_type
    try:
        if field_type == TemplateFieldType.INT:
            return int(value)
        if field_type == TemplateFieldType.DECIMAL:
            return Decimal(str(value))
        if field_type == TemplateFieldType.TEXT:
            return str(value)
    except (ValueError, TypeError) as exc:
        raise AttributeValidationError(
            f"Invalid value for field '{field.field_key}'."
        ) from exc
    if field_type == TemplateFieldType.ENUM:
        candidate = str(value)
        if field.enum_values and "values" in field.enum_values:
            allowed = set(field.enum_values.get("values", []))
            if candidate not in allowed:
                raise AttributeValidationError(
                    f"Value '{candidate}' not allowed for field '{field.field_key}'."
                )
        return candidate

    return value


def normalize_attributes(fields: list[TemplateField], attrs: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(attrs)

    for field in fields:
        key = field.field_key
        if key not in normalized and field.default_value is not None:
            normalized[key] = _coerce_value(field, field.default_value)

        if field.required and key not in normalized:
            raise AttributeValidationError(f"Missing required attribute: {key}")

        if key in normalized:
            normalized[key] = _coerce_value(field, normalized[key])

    return normalized


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _jsonable_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable_value(v) for v in value]

    return value


def to_jsonable(attrs: dict[str, Any]) -> dict[str, Any]:
    return {k: _jsonable_value(v) for k, v in attrs.items()}
