import hashlib

from app.db.models import ItemTemplate, SKUSequenceScope
from app.services.attributes import compute_attribute_hash


def test_compute_attribute_hash_uses_identity_fields() -> None:
    template = ItemTemplate(
        id=5,
        name="Widget",
        sku_prefix="WX",
        sku_pattern="{prefix}",
        seq_scope=SKUSequenceScope.GLOBAL,
        attribute_specs=[
            {"key": "a", "type": "int", "include_in_identity": True},
            {"key": "b", "type": "int", "include_in_identity": False},
        ],
        sku_rule={"prefix": "WX", "tokens": ["a"]},
    )
    attrs = {"b": 2, "a": 1}
    expected = hashlib.sha256('{"a":1}'.encode("utf-8")).hexdigest()
    assert compute_attribute_hash(template, attrs) == expected
