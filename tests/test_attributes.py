import pytest

from app.db.models import ItemTemplate, SKUSequenceScope
from app.services.attributes import AttributeValidationError, validate_and_normalize_attributes


def _template(attribute_specs: list[dict]) -> ItemTemplate:
    return ItemTemplate(
        id=1,
        name="Widget",
        sku_prefix="WX",
        sku_pattern="{prefix}",
        seq_scope=SKUSequenceScope.GLOBAL,
        attribute_specs=attribute_specs,
        sku_rule={"prefix": "WX", "tokens": []},
    )


def test_validate_and_normalize_attributes_coerces_types() -> None:
    template = _template(
        [
            {"key": "diameter", "type": "int", "required": True, "allowed_values": [95, 98]},
            {
                "key": "type",
                "type": "enum",
                "required": True,
                "allowed_values": ["mono", "multilayer"],
                "normalize": {"lower": True},
            },
        ]
    )
    result = validate_and_normalize_attributes(
        template, {"diameter": "98", "type": "MultiLayer"}
    )
    assert result == {"diameter": 98, "type": "multilayer"}


def test_validate_and_normalize_requires_missing_field() -> None:
    template = _template([{"key": "size", "type": "int", "required": True}])
    with pytest.raises(AttributeValidationError):
        validate_and_normalize_attributes(template, {})


def test_validate_and_normalize_validates_range_and_step() -> None:
    template = _template(
        [
            {
                "key": "thickness",
                "type": "int",
                "required": True,
                "allowed_range": {"min": 10, "max": 30, "step": 1},
            }
        ]
    )
    with pytest.raises(AttributeValidationError):
        validate_and_normalize_attributes(template, {"thickness": 9})
    with pytest.raises(AttributeValidationError):
        validate_and_normalize_attributes(template, {"thickness": 10.5})
    result = validate_and_normalize_attributes(template, {"thickness": 20})
    assert result["thickness"] == 20


def test_validate_and_normalize_rejects_unknown_keys() -> None:
    template = _template([{"key": "color", "type": "string"}])
    with pytest.raises(AttributeValidationError):
        validate_and_normalize_attributes(template, {"color": "blue", "extra": "nope"})
