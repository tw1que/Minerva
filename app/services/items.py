from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Item, ItemTemplate
from app.services.attributes import compute_attribute_hash, validate_and_normalize_attributes
from app.services.sku import build_product_code


class TemplateNotFoundError(LookupError):
    pass


class ItemVariantConflictError(ValueError):
    pass


class MedicalTraceabilityError(ValueError):
    pass


def get_item_by_hash(db: Session, template_id: int, attribute_hash: str) -> Item | None:
    stmt = select(Item).where(
        Item.template_id == template_id,
        Item.attribute_hash == attribute_hash,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_item_by_product_code(db: Session, product_code: str) -> Item | None:
    stmt = select(Item).where(Item.product_code == product_code)
    return db.execute(stmt).scalar_one_or_none()


def create_item_variant(
    db: Session,
    template_id: int,
    attrs: dict[str, Any],
    *,
    uom: str,
    track_lots: bool = True,
) -> tuple[Item, bool]:
    template = db.get(ItemTemplate, template_id)
    if not template:
        raise TemplateNotFoundError("Template not found.")

    if settings.medical_traceability and not track_lots:
        raise MedicalTraceabilityError("Medical traceability requires lot tracking.")

    canonical = validate_and_normalize_attributes(template, attrs)
    attribute_hash = compute_attribute_hash(template, canonical)

    existing = get_item_by_hash(db, template.id, attribute_hash)
    if existing:
        return existing, False

    product_code = build_product_code(template, canonical)
    if get_item_by_product_code(db, product_code):
        raise ItemVariantConflictError("Product code conflict/collision.")

    sku_rule_version = (template.sku_rule or {}).get("version", 1)

    item = Item(
        template_id=template.id,
        product_code=product_code,
        uom=uom,
        attributes=canonical,
        attribute_hash=attribute_hash,
        sku_rule_version=sku_rule_version,
        track_lots=track_lots,
    )

    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        existing = get_item_by_hash(db, template.id, attribute_hash)
        if existing:
            return existing, False
        if get_item_by_product_code(db, product_code):
            raise ItemVariantConflictError("Product code conflict/collision.") from exc
        raise ItemVariantConflictError("Item variant already exists.") from exc

    return item, True
