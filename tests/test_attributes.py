from datetime import datetime
from decimal import Decimal

import pytest

from app.db.models import TemplateField, TemplateFieldType, UserRole
from app.services.attributes import (
    AttributeValidationError,
    normalize_attributes,
    to_jsonable,
)


def _field(
    field_key: str,
    field_type: TemplateFieldType,
    *,
    required: bool = False,
    default_value: str | None = None,
    enum_values: dict | None = None,
) -> TemplateField:
    return TemplateField(
        template_id=1,
        field_key=field_key,
        field_type=field_type,
        required=required,
        default_value=default_value,
        enum_values=enum_values,
    )


def test_normalize_attributes_defaults_and_coercion() -> None:
    fields = [
        _field("size", TemplateFieldType.INT, required=True),
        _field("weight", TemplateFieldType.DECIMAL),
        _field("color", TemplateFieldType.TEXT, default_value="blue"),
    ]
    result = normalize_attributes(fields, {"size": "5", "weight": "1.25"})
    assert result["size"] == 5
    assert result["weight"] == Decimal("1.25")
    assert result["color"] == "blue"


def test_normalize_attributes_requires_missing_field() -> None:
    fields = [_field("size", TemplateFieldType.INT, required=True)]
    with pytest.raises(AttributeValidationError):
        normalize_attributes(fields, {})


def test_normalize_attributes_validates_enum_values() -> None:
    fields = [
        _field("grade", TemplateFieldType.ENUM, enum_values={"values": ["A", "B"]}),
    ]
    with pytest.raises(AttributeValidationError):
        normalize_attributes(fields, {"grade": "C"})


def test_to_jsonable_serializes_nested_types() -> None:
    attrs = {
        "qty": Decimal("1.5"),
        "ts": datetime(2024, 1, 1, 12, 0, 0),
        "role": UserRole.ADMIN,
        "nested": {"items": [Decimal("2.0")]},
    }
    jsonable = to_jsonable(attrs)
    assert jsonable["qty"] == "1.5"
    assert jsonable["ts"] == "2024-01-01T12:00:00"
    assert jsonable["role"] == "ADMIN"
    assert jsonable["nested"]["items"] == ["2.0"]
