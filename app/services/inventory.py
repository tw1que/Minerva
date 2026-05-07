from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Item,
    Lot,
    Manufacturer,
    MaterialClass,
    MovementReason,
    MovementReasonSign,
    Order,
    OrderLine,
    OrderMaterial,
    OrderStatus,
    Shade,
    StockLocation,
    StockMovement,
    StockReason,
    UnitOfMeasure,
)
from app.services.sku import assign_instance_seq, build_instance_sku


OPEN_ORDER_STATUSES = {
    OrderStatus.DRAFT,
    OrderStatus.RESERVED,
    OrderStatus.ALLOCATED,
}


class InventoryError(ValueError):
    pass


class InsufficientStockError(InventoryError):
    pass


class MovementReasonValidationError(InventoryError):
    pass


class LookupNotFoundError(LookupError):
    pass


@dataclass(slots=True)
class ReceiveStockCommand:
    item_id: int
    quantity: Decimal
    manufacturer_lot_code: str
    manufacturer_id: int | None = None
    material_class_id: int | None = None
    shade_id: int | None = None
    unit_id: int | None = None
    movement_reason_code: str = "RECEIPT"
    supplier_name: str | None = None
    manufacturing_date: datetime | None = None
    received_at: datetime | None = None
    expires_at: datetime | None = None
    certificate_ref: str | None = None
    notes: str | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    created_by: str | None = None
    comment: str | None = None


@dataclass(slots=True)
class ConsumeStockCommand:
    order_id: str
    item_id: int
    lot_id: int
    quantity: Decimal
    movement_reason_code: str = "CONSUME"
    unit_id: int | None = None
    used_by: str | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    comment: str | None = None


@dataclass(slots=True)
class AdjustStockCommand:
    item_id: int
    quantity_delta: Decimal
    movement_reason_code: str = "ADJUST"
    lot_id: int | None = None
    unit_id: int | None = None
    from_location_id: int | None = None
    to_location_id: int | None = None
    created_by: str | None = None
    comment: str | None = None
    ref_type: str | None = None
    ref_id: str | None = None


def get_on_hand_qty(db: Session, item_id: int) -> Decimal:
    stmt = select(func.coalesce(func.sum(StockMovement.qty_delta), 0)).where(
        StockMovement.item_id == item_id
    )
    value = db.execute(stmt).scalar_one()
    return Decimal(str(value))


def get_lot_on_hand_qty(db: Session, lot_id: int) -> Decimal:
    stmt = select(func.coalesce(func.sum(StockMovement.qty_delta), 0)).where(
        StockMovement.lot_id == lot_id
    )
    value = db.execute(stmt).scalar_one()
    return Decimal(str(value))


def get_reserved_qty(db: Session, item_id: int) -> Decimal:
    stmt = (
        select(func.coalesce(func.sum(OrderLine.qty_allocated), 0))
        .join(Order, Order.id == OrderLine.order_id)
        .where(OrderLine.item_id == item_id, Order.status.in_(OPEN_ORDER_STATUSES))
    )
    value = db.execute(stmt).scalar_one()
    return Decimal(str(value))


def get_available_qty(db: Session, item_id: int) -> Decimal:
    return get_on_hand_qty(db, item_id) - get_reserved_qty(db, item_id)


def get_stock_balance_rows(db: Session) -> list[tuple[int | None, Decimal]]:
    rows = db.execute(
        select(
            StockMovement.lot_id,
            func.coalesce(func.sum(StockMovement.qty_delta), 0).label("quantity_on_hand"),
        )
        .where(StockMovement.lot_id.is_not(None))
        .group_by(StockMovement.lot_id)
    ).all()
    return [(lot_id, Decimal(str(quantity_on_hand))) for lot_id, quantity_on_hand in rows]


def _get_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise LookupNotFoundError("Item not found.")
    return item


def _get_lot(db: Session, lot_id: int) -> Lot:
    lot = db.get(Lot, lot_id)
    if not lot:
        raise LookupNotFoundError("Lot not found.")
    return lot


def _get_unit(db: Session, unit_id: int | None, item: Item) -> UnitOfMeasure | None:
    resolved_unit_id = unit_id if unit_id is not None else item.unit_id
    if resolved_unit_id is None:
        return None
    unit = db.get(UnitOfMeasure, resolved_unit_id)
    if not unit:
        raise LookupNotFoundError("Unit of measure not found.")
    return unit


def _get_movement_reason(db: Session, code: str) -> MovementReason:
    stmt = select(MovementReason).where(MovementReason.code == code)
    reason = db.execute(stmt).scalar_one_or_none()
    if not reason:
        raise LookupNotFoundError("Movement reason not found.")
    return reason


def _get_lookup(db: Session, model, lookup_id: int | None, message: str):
    if lookup_id is None:
        return None
    value = db.get(model, lookup_id)
    if not value:
        raise LookupNotFoundError(message)
    return value


def _snapshot_codes(
    manufacturer: Manufacturer | None,
    material_class: MaterialClass | None,
    shade: Shade | None,
    item: Item,
) -> dict[str, str | None]:
    return {
        "manufacturer_code_snapshot": manufacturer.code if manufacturer else None,
        "material_class_code_snapshot": material_class.code if material_class else None,
        "shade_code_snapshot": shade.code if shade else None,
        "item_sku_snapshot": item.sku,
        "item_name_snapshot": item.display_name,
    }


def _enforce_reason_sign(reason: MovementReason, quantity: Decimal) -> None:
    if quantity == 0:
        raise MovementReasonValidationError("Quantity cannot be zero.")
    if reason.allowed_sign == MovementReasonSign.BOTH:
        return
    if reason.allowed_sign == MovementReasonSign.POSITIVE and quantity < 0:
        raise MovementReasonValidationError("Movement reason only allows positive quantities.")
    if reason.allowed_sign == MovementReasonSign.NEGATIVE and quantity > 0:
        raise MovementReasonValidationError("Movement reason only allows negative quantities.")


def _legacy_stock_reason(reason_code: str) -> StockReason | None:
    try:
        return StockReason[reason_code]
    except KeyError:
        return None


def create_lot_snapshot(
    db: Session,
    *,
    item: Item,
    manufacturer_lot_code: str,
    manufacturer_id: int | None = None,
    material_class_id: int | None = None,
    shade_id: int | None = None,
    supplier_name: str | None = None,
    manufacturing_date: datetime | None = None,
    received_at: datetime | None = None,
    expires_at: datetime | None = None,
    certificate_ref: str | None = None,
    notes: str | None = None,
) -> Lot:
    manufacturer = _get_lookup(db, Manufacturer, manufacturer_id, "Manufacturer not found.")
    material_class = _get_lookup(db, MaterialClass, material_class_id, "Material class not found.")
    shade = _get_lookup(db, Shade, shade_id, "Shade not found.")

    seq = assign_instance_seq(db, item)
    instance_sku = build_instance_sku(item.sku, seq)
    external_code = manufacturer_lot_code.strip()
    snapshot_values = _snapshot_codes(manufacturer, material_class, shade, item)

    lot = Lot(
        item_id=item.id,
        manufacturer_id=manufacturer_id,
        material_class_id=material_class_id,
        shade_id=shade_id,
        manufacturer_lot_code=external_code,
        lot_code=external_code,
        seq=seq,
        instance_sku=instance_sku,
        supplier_name=supplier_name,
        manufacturing_date=manufacturing_date,
        received_at=received_at or datetime.now(UTC),
        expires_at=expires_at,
        certificate_ref=certificate_ref,
        notes=notes,
        **snapshot_values,
    )
    db.add(lot)
    db.flush()
    return lot


def _build_movement(
    db: Session,
    *,
    item: Item,
    quantity: Decimal,
    unit_id: int | None,
    movement_reason_code: str,
    lot: Lot | None = None,
    from_location_id: int | None = None,
    to_location_id: int | None = None,
    ref_type: str | None = None,
    ref_id: str | None = None,
    created_by: str | None = None,
    comment: str | None = None,
) -> StockMovement:
    reason = _get_movement_reason(db, movement_reason_code)
    _enforce_reason_sign(reason, quantity)

    unit = _get_unit(db, unit_id, item)
    from_location = _get_lookup(db, StockLocation, from_location_id, "From location not found.")
    to_location = _get_lookup(db, StockLocation, to_location_id, "To location not found.")

    movement = StockMovement(
        item_id=item.id,
        lot_id=lot.id if lot else None,
        qty_delta=quantity,
        unit_id=unit.id if unit else None,
        unit_code_snapshot=unit.code if unit else item.uom,
        uom=unit.code if unit else item.uom,
        movement_reason_id=reason.id,
        movement_reason_code_snapshot=reason.code,
        reason=_legacy_stock_reason(reason.code),
        from_location_id=from_location.id if from_location else None,
        from_location_code_snapshot=from_location.code if from_location else None,
        to_location_id=to_location.id if to_location else None,
        to_location_code_snapshot=to_location.code if to_location else None,
        ref_type=ref_type,
        ref_id=ref_id,
        created_by=created_by,
        comment=comment,
    )
    db.add(movement)
    db.flush()
    return movement


def receive_stock(db: Session, command: ReceiveStockCommand) -> tuple[Lot, StockMovement]:
    if command.quantity <= 0:
        raise InventoryError("Receipt quantity must be positive.")

    item = _get_item(db, command.item_id)

    try:
        lot = create_lot_snapshot(
            db,
            item=item,
            manufacturer_lot_code=command.manufacturer_lot_code,
            manufacturer_id=command.manufacturer_id,
            material_class_id=command.material_class_id,
            shade_id=command.shade_id,
            supplier_name=command.supplier_name,
            manufacturing_date=command.manufacturing_date,
            received_at=command.received_at,
            expires_at=command.expires_at,
            certificate_ref=command.certificate_ref,
            notes=command.notes,
        )
        movement = _build_movement(
            db,
            item=item,
            lot=lot,
            quantity=command.quantity,
            unit_id=command.unit_id,
            movement_reason_code=command.movement_reason_code,
            ref_type=command.ref_type,
            ref_id=command.ref_id,
            created_by=command.created_by,
            comment=command.comment,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(lot)
    db.refresh(movement)
    return lot, movement


def consume_stock(db: Session, command: ConsumeStockCommand) -> tuple[OrderMaterial, StockMovement]:
    if command.quantity <= 0:
        raise InventoryError("Consumption quantity must be positive.")

    item = _get_item(db, command.item_id)
    lot = _get_lot(db, command.lot_id)
    if lot.item_id != item.id:
        raise LookupNotFoundError("Lot not found for item.")

    available = get_lot_on_hand_qty(db, lot.id)
    if available < command.quantity:
        raise InsufficientStockError(f"Not enough stock in lot. Available: {available}")

    try:
        movement = _build_movement(
            db,
            item=item,
            lot=lot,
            quantity=-command.quantity,
            unit_id=command.unit_id,
            movement_reason_code=command.movement_reason_code,
            ref_type=command.ref_type,
            ref_id=command.ref_id,
            created_by=command.used_by,
            comment=command.comment,
        )
        order_material = OrderMaterial(
            order_id=command.order_id,
            item_id=item.id,
            lot_id=lot.id,
            qty_used=command.quantity,
            unit_id=movement.unit_id,
            unit_code_snapshot=movement.unit_code_snapshot,
            item_sku_snapshot=lot.item_sku_snapshot or item.sku,
            item_name_snapshot=lot.item_name_snapshot or item.display_name,
            lot_code_snapshot=lot.manufacturer_lot_code or lot.lot_code,
            material_class_code_snapshot=lot.material_class_code_snapshot,
            shade_code_snapshot=lot.shade_code_snapshot,
            used_by=command.used_by,
            stock_movement_id=movement.id,
        )
        db.add(order_material)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(movement)
    db.refresh(order_material)
    return order_material, movement


def adjust_stock(db: Session, command: AdjustStockCommand) -> StockMovement:
    if not command.comment:
        raise InventoryError("Adjustment requires a comment.")

    item = _get_item(db, command.item_id)
    lot = None
    if command.lot_id is not None:
        lot = _get_lot(db, command.lot_id)
        if lot.item_id != item.id:
            raise LookupNotFoundError("Lot not found for item.")

    if command.quantity_delta < 0 and lot is not None:
        available = get_lot_on_hand_qty(db, lot.id)
        if available + command.quantity_delta < 0:
            raise InsufficientStockError(f"Not enough stock in lot. Available: {available}")
    elif command.quantity_delta < 0:
        available = get_available_qty(db, item.id)
        if available + command.quantity_delta < 0:
            raise InsufficientStockError(f"Not enough available stock. Available: {available}")

    try:
        movement = _build_movement(
            db,
            item=item,
            lot=lot,
            quantity=command.quantity_delta,
            unit_id=command.unit_id,
            movement_reason_code=command.movement_reason_code,
            from_location_id=command.from_location_id,
            to_location_id=command.to_location_id,
            ref_type=command.ref_type,
            ref_id=command.ref_id,
            created_by=command.created_by,
            comment=command.comment,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(movement)
    return movement
