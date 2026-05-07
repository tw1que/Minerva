from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    AttributeType,
    Item,
    ItemBlank,
    ItemIvobaseCartridge,
    ItemTemplate,
    Manufacturer,
    MaterialClass,
    Shade,
    UnitOfMeasure,
)
from app.services.attributes import compute_attribute_hash, validate_and_normalize_attributes
from app.services.sku import build_product_code


class TemplateNotFoundError(LookupError):
    pass


class ItemVariantConflictError(ValueError):
    pass


class MedicalTraceabilityError(ValueError):
    pass


class ManufacturerNotFoundError(LookupError):
    pass


class UnitOfMeasureNotFoundError(LookupError):
    pass


class MaterialClassNotFoundError(LookupError):
    pass


class ShadeNotFoundError(LookupError):
    pass


class ItemTypeMismatchError(ValueError):
    pass


@dataclass(slots=True)
class ItemBlankPayload:
    diameter_mm: Decimal
    thickness_mm: Decimal
    material_class_id: int
    shade_id: int | None = None
    is_multilayer: bool = False


@dataclass(slots=True)
class ItemIvobaseCartridgePayload:
    material_class_id: int
    size_code: str
    shade_id: int | None = None


def _merge_enum_values(template: ItemTemplate, canonical: dict[str, Any]) -> bool:
    specs = template.attribute_specs or []
    if not isinstance(specs, list):
        return False
    changed = False
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        if str(spec.get("type", "")).lower() != AttributeType.ENUM.value:
            continue
        key = spec.get("key")
        if not key or key not in canonical:
            continue
        value = canonical.get(key)
        if value is None:
            continue
        allowed_values = spec.get("allowed_values")
        if not isinstance(allowed_values, list):
            allowed_values = []
        allowed_set = {str(item) for item in allowed_values}
        if str(value) not in allowed_set:
            allowed_values.append(value)
            spec["allowed_values"] = allowed_values
            changed = True
    if changed:
        template.attribute_specs = specs
    return changed


def get_item_by_hash(db: Session, template_id: int, attribute_hash: str) -> Item | None:
    stmt = select(Item).where(
        Item.template_id == template_id,
        Item.attribute_hash == attribute_hash,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_item_by_sku(db: Session, sku: str) -> Item | None:
    stmt = select(Item).where(Item.sku == sku)
    return db.execute(stmt).scalar_one_or_none()


def get_item_by_product_code(db: Session, product_code: str) -> Item | None:
    return get_item_by_sku(db, product_code)


def _require_manufacturer(db: Session, manufacturer_id: int | None) -> Manufacturer | None:
    if manufacturer_id is None:
        return None
    manufacturer = db.get(Manufacturer, manufacturer_id)
    if not manufacturer:
        raise ManufacturerNotFoundError("Manufacturer not found.")
    return manufacturer


def _require_unit(db: Session, unit_id: int | None) -> UnitOfMeasure | None:
    if unit_id is None:
        return None
    unit = db.get(UnitOfMeasure, unit_id)
    if not unit:
        raise UnitOfMeasureNotFoundError("Unit of measure not found.")
    return unit


def _require_material_class(db: Session, material_class_id: int) -> MaterialClass:
    material_class = db.get(MaterialClass, material_class_id)
    if not material_class:
        raise MaterialClassNotFoundError("Material class not found.")
    return material_class


def _require_shade(db: Session, shade_id: int | None) -> Shade | None:
    if shade_id is None:
        return None
    shade = db.get(Shade, shade_id)
    if not shade:
        raise ShadeNotFoundError("Shade not found.")
    return shade


def create_item_variant(
    db: Session,
    template_id: int,
    attrs: dict[str, Any],
    *,
    uom: str,
    track_lots: bool = True,
    manufacturer_id: int | None = None,
) -> tuple[Item, bool]:
    template = db.get(ItemTemplate, template_id)
    if not template:
        raise TemplateNotFoundError("Template not found.")

    _require_manufacturer(db, manufacturer_id)

    if settings.medical_traceability and not track_lots:
        raise MedicalTraceabilityError("Medical traceability requires lot tracking.")

    canonical = validate_and_normalize_attributes(
        template,
        attrs,
        allow_new_enum_values=True,
    )
    attribute_hash = compute_attribute_hash(template, canonical)

    existing = get_item_by_hash(db, template.id, attribute_hash)
    if existing:
        if _merge_enum_values(template, canonical):
            db.commit()
        return existing, False

    sku = build_product_code(template, canonical)
    if get_item_by_sku(db, sku):
        raise ItemVariantConflictError("Product code conflict/collision.")

    _merge_enum_values(template, canonical)
    sku_rule_version = (template.sku_rule or {}).get("version", 1)

    item = Item(
        item_type=template.item_type,
        template_id=template.id,
        manufacturer_id=manufacturer_id,
        sku=sku,
        name=sku,
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
        if get_item_by_sku(db, sku):
            raise ItemVariantConflictError("Product code conflict/collision.") from exc
        raise ItemVariantConflictError("Item variant already exists.") from exc

    return item, True


def create_relational_item(
    db: Session,
    *,
    item_type: str,
    sku: str,
    name: str,
    unit_id: int | None,
    manufacturer_id: int | None = None,
    template_id: int | None = None,
    track_lots: bool = True,
    metadata: dict[str, Any] | None = None,
    legacy_attributes: dict[str, Any] | None = None,
    blank_details: ItemBlankPayload | None = None,
    ivobase_cartridge_details: ItemIvobaseCartridgePayload | None = None,
) -> Item:
    if not item_type.strip():
        raise ItemTypeMismatchError("Item type is required.")
    if not sku.strip():
        raise ItemVariantConflictError("SKU is required.")
    if not name.strip():
        raise ItemVariantConflictError("Item name is required.")
    if settings.medical_traceability and not track_lots:
        raise MedicalTraceabilityError("Medical traceability requires lot tracking.")
    if get_item_by_sku(db, sku.strip()):
        raise ItemVariantConflictError("SKU already exists.")

    template = None
    if template_id is not None:
        template = db.get(ItemTemplate, template_id)
        if not template:
            raise TemplateNotFoundError("Template not found.")
        if template.item_type and template.item_type != item_type:
            raise ItemTypeMismatchError("Template item_type does not match item.")

    _require_manufacturer(db, manufacturer_id)
    unit = _require_unit(db, unit_id)

    if blank_details and ivobase_cartridge_details:
        raise ItemTypeMismatchError("Provide one typed item detail payload per item.")

    item = Item(
        item_type=item_type.strip(),
        template_id=template_id,
        manufacturer_id=manufacturer_id,
        unit_id=unit_id,
        sku=sku.strip(),
        name=name.strip(),
        metadata_json=metadata or {},
        attributes=legacy_attributes or {},
        attribute_hash=None,
        track_lots=track_lots,
        uom=unit.code if unit else None,
    )

    if blank_details:
        _require_material_class(db, blank_details.material_class_id)
        _require_shade(db, blank_details.shade_id)
        item.blank_details = ItemBlank(
            diameter_mm=blank_details.diameter_mm,
            thickness_mm=blank_details.thickness_mm,
            material_class_id=blank_details.material_class_id,
            shade_id=blank_details.shade_id,
            is_multilayer=blank_details.is_multilayer,
        )
    elif ivobase_cartridge_details:
        _require_material_class(db, ivobase_cartridge_details.material_class_id)
        _require_shade(db, ivobase_cartridge_details.shade_id)
        item.ivobase_cartridge_details = ItemIvobaseCartridge(
            material_class_id=ivobase_cartridge_details.material_class_id,
            size_code=ivobase_cartridge_details.size_code.strip(),
            shade_id=ivobase_cartridge_details.shade_id,
        )

    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        if get_item_by_sku(db, sku.strip()):
            raise ItemVariantConflictError("SKU already exists.") from exc
        raise ItemVariantConflictError("Unable to create item.") from exc

    return item
