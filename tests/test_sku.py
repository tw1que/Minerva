from datetime import datetime

import pytest

from app.db.models import ItemTemplate, SKUSequenceScope, TemplateField, TemplateFieldType
from app.services import sku


def _template(*, scope: SKUSequenceScope = SKUSequenceScope.GLOBAL) -> ItemTemplate:
    return ItemTemplate(
        id=7,
        name="Widget",
        sku_prefix="WX",
        sku_pattern="{prefix}-{color}-{seq:04d}",
        seq_scope=scope,
    )


def _field(*, format_value: str | None = None, include_in_sku: bool = True) -> TemplateField:
    return TemplateField(
        template_id=7,
        field_key="color",
        field_type=TemplateFieldType.TEXT,
        include_in_sku=include_in_sku,
        sku_order=1,
        format=format_value,
    )


def test_format_value_variants() -> None:
    field = _field(format_value="upper")
    assert sku._format_value("red", field) == "RED"

    field.format = "lower"
    assert sku._format_value("Red", field) == "red"

    field.format = "title"
    assert sku._format_value("red widget", field) == "Red Widget"

    field.format = "zfill:4"
    assert sku._format_value("7", field) == "0007"


def test_format_value_invalid_zfill_raises() -> None:
    field = _field(format_value="zfill:bad")
    with pytest.raises(sku.SKUGenerationError):
        sku._format_value("7", field)


def test_scope_key_variants() -> None:
    template = _template(scope=SKUSequenceScope.GLOBAL)
    assert sku._scope_key(template) == "GLOBAL"

    template.seq_scope = SKUSequenceScope.PER_TEMPLATE
    assert sku._scope_key(template) == "T:7"

    template.seq_scope = SKUSequenceScope.PER_PREFIX
    assert sku._scope_key(template) == "P:WX"


def test_scope_key_per_year_uses_current_year(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return datetime(2024, 1, 1)

    template = _template(scope=SKUSequenceScope.PER_YEAR)
    monkeypatch.setattr(sku, "datetime", FixedDatetime)
    assert sku._scope_key(template) == "Y:2024"


def test_generate_sku_builds_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    template = _template()
    field = _field(format_value="upper")
    template.fields = [field]
    field.template = template

    monkeypatch.setattr(sku, "_next_sequence", lambda db, template: 12)
    result = sku.generate_sku(object(), template, {"color": "red"})
    assert result == "WX-RED-0012"


def test_generate_sku_missing_attribute_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    template = _template()
    field = _field()
    template.fields = [field]
    field.template = template

    monkeypatch.setattr(sku, "_next_sequence", lambda db, template: 1)
    with pytest.raises(sku.SKUGenerationError):
        sku.generate_sku(object(), template, {})
