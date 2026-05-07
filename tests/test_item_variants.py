import pytest

from app.db.models import Item, ItemTemplate, SKUCounter, SKUSequenceScope
from app.services import items as items_service
from app.services.items import ItemVariantConflictError, create_item_variant


class FakeSession:
    def __init__(self, template: ItemTemplate | None) -> None:
        self._template = template
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False
        self.counter_touched = False

    def get(self, model, pk):  # type: ignore[override]
        if model is ItemTemplate and self._template and pk == self._template.id:
            return self._template
        return None

    def add(self, obj) -> None:
        if isinstance(obj, SKUCounter):
            self.counter_touched = True
        self.added.append(obj)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, obj) -> None:
        return None

    def rollback(self) -> None:
        self.rolled_back = True


def _template() -> ItemTemplate:
    return ItemTemplate(
        id=22,
        name="Template",
        sku_prefix="TMP",
        sku_pattern="{prefix}",
        seq_scope=SKUSequenceScope.GLOBAL,
        attribute_specs=[{"key": "size", "type": "int", "required": True}],
        sku_rule={"prefix": "TMP", "tokens": ["size"]},
    )


def test_create_item_variant_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    template = _template()
    db = FakeSession(template)
    existing = Item(
        template_id=template.id,
        product_code="TMP-5",
        uom="EA",
        attributes={"size": 5},
        attribute_hash="hash",
        track_lots=True,
    )

    monkeypatch.setattr(items_service, "get_item_by_hash", lambda *_: existing)
    monkeypatch.setattr(items_service, "get_item_by_sku", lambda *_: None)

    item, created = create_item_variant(db, template.id, {"size": 5}, uom="EA")
    assert item is existing
    assert created is False
    assert db.added == []


def test_create_item_variant_product_code_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    template = _template()
    db = FakeSession(template)
    existing = Item(
        template_id=template.id,
        product_code="TMP-5",
        uom="EA",
        attributes={"size": 5},
        attribute_hash="other-hash",
        track_lots=True,
    )

    monkeypatch.setattr(items_service, "get_item_by_hash", lambda *_: None)
    monkeypatch.setattr(items_service, "get_item_by_sku", lambda *_: existing)

    with pytest.raises(ItemVariantConflictError):
        create_item_variant(db, template.id, {"size": 5}, uom="EA")


def test_item_unique_constraints_present() -> None:
    constraints = {constraint.name: constraint for constraint in Item.__table__.constraints}
    assert "uq_item_variant" in constraints
    assert Item.__table__.c.sku.unique is True
    column_names = {col.name for col in constraints["uq_item_variant"].columns}
    assert column_names == {"template_id", "attribute_hash"}


def test_create_item_variant_does_not_touch_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    template = _template()
    db = FakeSession(template)

    monkeypatch.setattr(items_service, "get_item_by_hash", lambda *_: None)
    monkeypatch.setattr(items_service, "get_item_by_sku", lambda *_: None)

    item, created = create_item_variant(db, template.id, {"size": 5}, uom="EA")
    assert created is True
    assert item.product_code == "TMP-5"
    assert db.counter_touched is False


def test_create_item_variant_expands_enum_values(monkeypatch: pytest.MonkeyPatch) -> None:
    template = ItemTemplate(
        id=33,
        name="Shade Template",
        sku_prefix="SHD",
        sku_pattern="{prefix}",
        seq_scope=SKUSequenceScope.GLOBAL,
        attribute_specs=[
            {"key": "shade", "type": "enum", "required": True, "allowed_values": ["A1"]}
        ],
        sku_rule={"prefix": "SHD", "tokens": ["shade"]},
    )
    db = FakeSession(template)

    monkeypatch.setattr(items_service, "get_item_by_hash", lambda *_: None)
    monkeypatch.setattr(items_service, "get_item_by_sku", lambda *_: None)

    item, created = create_item_variant(db, template.id, {"shade": "A2"}, uom="EA")
    assert created is True
    assert item.product_code == "SHD-A2"
    assert template.attribute_specs[0]["allowed_values"] == ["A1", "A2"]
