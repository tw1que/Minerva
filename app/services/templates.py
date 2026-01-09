from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ItemTemplate, Manufacturer, SKUSequenceScope
from app.schemas.template import TemplateCreate


class ManufacturerNotFoundError(LookupError):
    pass


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
    if payload.manufacturer_id is not None:
        manufacturer = db.get(Manufacturer, payload.manufacturer_id)
        if not manufacturer:
            raise ManufacturerNotFoundError("Manufacturer not found.")

    attribute_specs = [spec.model_dump(mode="json") for spec in payload.attribute_specs]
    sku_rule = payload.sku_rule.model_dump(mode="json")

    template = ItemTemplate(
        name=payload.name,
        manufacturer_id=payload.manufacturer_id,
        attribute_specs=attribute_specs,
        sku_rule=sku_rule,
        sku_prefix=sku_rule.get("prefix", ""),
        sku_pattern=_legacy_sku_pattern(sku_rule),
        seq_scope=SKUSequenceScope.PER_TEMPLATE,
    )

    try:
        db.add(template)
        db.commit()
        db.refresh(template)
    except IntegrityError as exc:
        db.rollback()
        raise TemplateConflictError("Template already exists.") from exc

    return template
