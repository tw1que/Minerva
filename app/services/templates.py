from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ItemTemplate, SKUSequenceScope
from app.schemas.template import TemplateCreate


class TemplateConflictError(ValueError):
    pass


def _legacy_sku_pattern(sku_rule: dict) -> str:
    prefix_placeholder = "{prefix}"
    tokens = sku_rule.get("tokens") or []
    separator = sku_rule.get("separator", "-")
    if not tokens:
        return prefix_placeholder
    placeholders = [f"{{{token}}}" for token in tokens]
    return separator.join([prefix_placeholder] + placeholders)


def create_template(db: Session, payload: TemplateCreate) -> ItemTemplate:
    name = payload.name.strip()
    attribute_specs = [spec.model_dump(mode="json") for spec in payload.attribute_specs]
    sku_rule = payload.sku_rule.model_dump(mode="json")

    existing = db.execute(
        select(ItemTemplate).where(func.lower(ItemTemplate.name) == func.lower(name))
    ).scalars().all()
    for template in existing:
        if template.attribute_specs == attribute_specs and template.sku_rule == sku_rule:
            raise TemplateConflictError("Template already exists.")

    template = ItemTemplate(
        name=name,
        item_type=payload.item_type.strip() if payload.item_type else None,
        attribute_specs=attribute_specs,
        sku_rule=sku_rule,
        sku_prefix=sku_rule.get("prefix", ""),
        sku_pattern=_legacy_sku_pattern(sku_rule),
        seq_scope=SKUSequenceScope.PER_TEMPLATE,
        display_pattern=payload.display_pattern,
        form_config=payload.form_config,
    )

    try:
        db.add(template)
        db.commit()
        db.refresh(template)
    except IntegrityError as exc:
        db.rollback()
        raise TemplateConflictError("Template already exists.") from exc

    return template
