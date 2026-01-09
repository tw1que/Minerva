from app.db.models import ItemTemplate, SKUSequenceScope
from app.services.attributes import validate_and_normalize_attributes
from app.services.sku import build_instance_sku, build_product_code


def _template_blanks() -> ItemTemplate:
    return ItemTemplate(
        id=10,
        name="Blanks",
        sku_prefix="BLK",
        sku_pattern="{prefix}",
        seq_scope=SKUSequenceScope.GLOBAL,
        attribute_specs=[
            {"key": "diameter", "type": "int", "required": True},
            {"key": "thickness", "type": "int", "required": True},
            {"key": "color", "type": "enum", "required": True, "allowed_values": ["A1", "A2"]},
            {
                "key": "type",
                "type": "enum",
                "required": True,
                "allowed_values": ["mono", "multilayer"],
                "normalize": {"lower": True},
                "sku_map": {"mono": "MO", "multilayer": "ML"},
            },
        ],
        sku_rule={
            "prefix": "BLK",
            "separator": "-",
            "tokens": ["diameter", "thickness", "color", "type"],
        },
    )


def _template_ivobase() -> ItemTemplate:
    return ItemTemplate(
        id=11,
        name="Ivobase",
        sku_prefix="IVO",
        sku_pattern="{prefix}",
        seq_scope=SKUSequenceScope.GLOBAL,
        attribute_specs=[
            {"key": "size", "type": "enum", "required": True, "allowed_values": ["S", "M", "L"]},
            {"key": "shade", "type": "enum", "required": False, "allowed_values": ["A1", "A2"]},
        ],
        sku_rule={"prefix": "IVO", "tokens": ["size", "shade"]},
    )


def test_build_product_code_for_blanks() -> None:
    template = _template_blanks()
    attrs = validate_and_normalize_attributes(
        template, {"diameter": 98, "thickness": 20, "color": "A2", "type": "multilayer"}
    )
    assert build_product_code(template, attrs) == "BLK-98-20-A2-ML"


def test_build_product_code_skips_optional_tokens() -> None:
    template = _template_ivobase()
    attrs = validate_and_normalize_attributes(template, {"size": "M"})
    assert build_product_code(template, attrs) == "IVO-M"


def test_build_product_code_is_deterministic() -> None:
    template = _template_blanks()
    attrs = validate_and_normalize_attributes(
        template, {"diameter": 98, "thickness": 20, "color": "A2", "type": "mono"}
    )
    first = build_product_code(template, attrs)
    second = build_product_code(template, attrs)
    assert first == second


def test_build_instance_sku_uses_padding() -> None:
    assert build_instance_sku("BLK-98-20-A2", 42) == "BLK-98-20-A2-0042"
