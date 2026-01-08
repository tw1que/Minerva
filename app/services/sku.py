from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ItemTemplate, SKUCounter, SKUSequenceScope, TemplateField


class SKUGenerationError(ValueError):
    pass


def _scope_key(template: ItemTemplate) -> str:
    scope = template.seq_scope
    if scope == SKUSequenceScope.GLOBAL:
        return "GLOBAL"
    if scope == SKUSequenceScope.PER_TEMPLATE:
        return f"T:{template.id}"
    if scope == SKUSequenceScope.PER_PREFIX:
        return f"P:{template.sku_prefix}"
    if scope == SKUSequenceScope.PER_YEAR:
        return f"Y:{datetime.utcnow().year}"

    return "GLOBAL"


def _next_sequence(db: Session, template: ItemTemplate) -> int:
    key = _scope_key(template)
    stmt = (
        select(SKUCounter)
        .where(SKUCounter.template_id == template.id, SKUCounter.scope_key == key)
        .with_for_update()
    )
    counter = db.execute(stmt).scalar_one_or_none()
    if counter is None:
        counter = SKUCounter(template_id=template.id, scope_key=key, next_seq=1)
        db.add(counter)
        db.flush()

    seq = int(counter.next_seq)
    counter.next_seq = seq + 1
    return seq


def _format_value(value: Any, field: TemplateField) -> str:
    text = str(value)
    if not field.format:
        return text

    fmt = field.format
    if fmt == "upper":
        return text.upper()
    if fmt == "lower":
        return text.lower()
    if fmt == "title":
        return text.title()
    if fmt.startswith("zfill:"):
        try:
            width = int(fmt.split(":", 1)[1])
        except ValueError as exc:
            raise SKUGenerationError(f"Invalid zfill width for {field.field_key}") from exc
        return text.zfill(width)

    return text


def generate_sku(
    db: Session,
    template: ItemTemplate,
    attributes: dict[str, Any],
) -> str:
    seq = _next_sequence(db, template)
    context: dict[str, Any] = {"prefix": template.sku_prefix, "seq": seq}

    for field in sorted(
        [f for f in template.fields if f.include_in_sku],
        key=lambda f: (f.sku_order or 0, f.field_key),
    ):
        if field.field_key not in attributes:
            raise SKUGenerationError(f"Missing SKU attribute: {field.field_key}")
        context[field.field_key] = _format_value(attributes[field.field_key], field)

    try:
        return template.sku_pattern.format_map(context)
    except KeyError as exc:
        raise SKUGenerationError(f"Missing SKU placeholder: {exc.args[0]}") from exc
