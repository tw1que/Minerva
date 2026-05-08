from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Item,
    ItemBlank,
    ItemIvobaseCartridge,
    Lot,
    Manufacturer,
    MaterialClass,
    MovementReason,
    MovementReasonSign,
    Order,
    OrderMaterial,
    Shade,
    StockLocation,
    StockMovement,
)


class InventoryValidationError(ValueError):
    pass


class InsufficientStockError(InventoryValidationError):
    pass


@dataclass(slots=True)
class ReceiveStockInput:
    item_id: int
    quantity: Decimal
    movement_reason_id: int
    manufacturer_lot_code: str
    manufacturer_id: int | None = None
    material_class_id: int | None = None
    shade_id: int | None = None
    lot_code: str | None = None
    to_location_id: int | None = None
    received_at: datetime | None = None
    expires_at: datetime | None = None
    certificate_ref: str | None = None
    notes: str | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    moved_by: str | None = None
    created_by: str | None = None
    comment: str | None = None


@dataclass(slots=True)
class AdjustStockInput:
    item_id: int
    qty_delta: Decimal
    movement_reason_id: int
    comment: str
    lot_id: int | None = None
    from_location_id: int | None = None
    to_location_id: int | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    moved_by: str | None = None
    created_by: str | None = None


@dataclass(slots=True)
class ConsumeStockInput:
    order_id: int
    item_id: int
    lot_id: int
    quantity: Decimal
    movement_reason_id: int
    used_by: str | None = None
    created_by: str | None = None
    comment: str | None = None
    from_location_id: int | None = None
    ref_type: str | None = "order_material"
    ref_id: str | None = None


def receive_stock(db: Session, payload: ReceiveStockInput) -> tuple[Lot, StockMovement]:
    try:
        if payload.quantity <= 0:
            raise InventoryValidationError("Received quantity must be positive.")
        if not payload.manufacturer_lot_code.strip():
            raise InventoryValidationError("manufacturer_lot_code is required.")

        item = _get_item(db, payload.item_id)
        reason = _get_reason(db, payload.movement_reason_id)
        _enforce_reason_sign(reason, payload.quantity)

        manufacturer_id = _resolve_manufacturer_id(db, item, payload.manufacturer_id)
        material_class_id = _resolve_material_class_id(db, item, payload.material_class_id)
        shade_id = _resolve_shade_id(db, item, payload.shade_id)
        to_location = _get_location(db, payload.to_location_id)
        lot_code = payload.lot_code.strip() if payload.lot_code and payload.lot_code.strip() else payload.manufacturer_lot_code.strip()

        lot = Lot(
            item_id=item.id,
            manufacturer_id=manufacturer_id,
            material_class_id=material_class_id,
            shade_id=shade_id,
            manufacturer_lot_code=payload.manufacturer_lot_code.strip(),
            lot_code=lot_code,
            instance_sku=_build_instance_sku(item.sku, lot_code),
            received_at=payload.received_at or datetime.now(timezone.utc),
            expires_at=payload.expires_at,
            certificate_ref=payload.certificate_ref,
            notes=payload.notes,
            item_sku_snapshot=item.sku,
            item_name_snapshot=item.name,
            manufacturer_code_snapshot=_lookup_code(db, Manufacturer, manufacturer_id),
            material_class_code_snapshot=_lookup_code(db, MaterialClass, material_class_id),
            shade_code_snapshot=_lookup_code(db, Shade, shade_id),
        )
        db.add(lot)
        db.flush()

        movement = _build_movement(
            item=item,
            lot=lot,
            qty_delta=payload.quantity,
            movement_reason=reason,
            from_location=None,
            to_location=to_location,
            ref_type=payload.ref_type,
            ref_id=payload.ref_id,
            moved_by=payload.moved_by,
            created_by=payload.created_by,
            comment=payload.comment,
        )
        db.add(movement)
        db.commit()
        db.refresh(lot)
        db.refresh(movement)
        return lot, movement
    except Exception:
        db.rollback()
        raise


def adjust_stock(db: Session, payload: AdjustStockInput) -> StockMovement:
    try:
        if payload.qty_delta == 0:
            raise InventoryValidationError("qty_delta must not be zero.")
        if not payload.comment or not payload.comment.strip():
            raise InventoryValidationError("comment is required for manual adjustments.")

        item = _get_item(db, payload.item_id)
        reason = _get_reason(db, payload.movement_reason_id)
        _enforce_reason_sign(reason, payload.qty_delta)
        lot = _get_lot(db, payload.lot_id) if payload.lot_id is not None else None
        from_location = _get_location(db, payload.from_location_id)
        to_location = _get_location(db, payload.to_location_id)
        if lot and lot.item_id != item.id:
            raise InventoryValidationError("Lot does not belong to item.")
        if payload.qty_delta < 0:
            available = get_lot_balance(db, lot.id) if lot else get_item_balance(db, item.id)
            if available + payload.qty_delta < 0:
                raise InsufficientStockError("Adjustment would make stock negative.")

        movement = _build_movement(
            item=item,
            lot=lot,
            qty_delta=payload.qty_delta,
            movement_reason=reason,
            from_location=from_location,
            to_location=to_location,
            ref_type=payload.ref_type,
            ref_id=payload.ref_id,
            moved_by=payload.moved_by,
            created_by=payload.created_by,
            comment=payload.comment.strip(),
        )
        db.add(movement)
        db.commit()
        db.refresh(movement)
        return movement
    except Exception:
        db.rollback()
        raise


def consume_stock(db: Session, payload: ConsumeStockInput) -> tuple[StockMovement, OrderMaterial]:
    try:
        if payload.quantity <= 0:
            raise InventoryValidationError("Consumed quantity must be positive.")

        order = db.get(Order, payload.order_id)
        if not order:
            raise InventoryValidationError("Order not found.")
        item = _get_item(db, payload.item_id)
        lot = _get_lot(db, payload.lot_id)
        from_location = _get_location(db, payload.from_location_id)
        if lot.item_id != item.id:
            raise InventoryValidationError("Lot does not belong to item.")
        reason = _get_reason(db, payload.movement_reason_id)
        _enforce_reason_sign(reason, payload.quantity * Decimal("-1"))
        if get_lot_balance(db, lot.id) < payload.quantity:
            raise InsufficientStockError("Cannot consume more than current lot balance.")

        movement = _build_movement(
            item=item,
            lot=lot,
            qty_delta=payload.quantity * Decimal("-1"),
            movement_reason=reason,
            from_location=from_location,
            to_location=None,
            ref_type=payload.ref_type,
            ref_id=payload.ref_id or str(order.id),
            moved_by=payload.used_by,
            created_by=payload.created_by,
            comment=payload.comment,
        )
        db.add(movement)
        db.flush()

        order_material = OrderMaterial(
            order_id=order.id,
            item_id=item.id,
            lot_id=lot.id,
            qty_used=payload.quantity,
            unit_id=item.unit_id,
            unit_code_snapshot=item.unit.code,
            item_sku_snapshot=lot.item_sku_snapshot,
            item_name_snapshot=lot.item_name_snapshot,
            lot_code_snapshot=lot.lot_code,
            material_class_code_snapshot=lot.material_class_code_snapshot,
            shade_code_snapshot=lot.shade_code_snapshot,
            stock_movement_id=movement.id,
            used_at=movement.moved_at,
            used_by=payload.used_by,
        )
        db.add(order_material)
        db.commit()
        db.refresh(movement)
        db.refresh(order_material)
        return movement, order_material
    except Exception:
        db.rollback()
        raise


def get_lot_balance(db: Session, lot_id: int) -> Decimal:
    value = db.execute(
        select(func.coalesce(func.sum(StockMovement.qty_delta), 0)).where(StockMovement.lot_id == lot_id)
    ).scalar_one()
    return Decimal(value)


def get_item_balance(db: Session, item_id: int) -> Decimal:
    value = db.execute(
        select(func.coalesce(func.sum(StockMovement.qty_delta), 0)).where(StockMovement.item_id == item_id)
    ).scalar_one()
    return Decimal(value)


def list_lot_balances(db: Session) -> list[tuple[int, Decimal]]:
    rows = db.execute(
        select(StockMovement.lot_id, func.sum(StockMovement.qty_delta))
        .where(StockMovement.lot_id.is_not(None))
        .group_by(StockMovement.lot_id)
        .order_by(StockMovement.lot_id)
    ).all()
    return [(row[0], Decimal(row[1])) for row in rows]


def list_item_balances(db: Session) -> list[tuple[int, Decimal]]:
    rows = db.execute(
        select(StockMovement.item_id, func.sum(StockMovement.qty_delta))
        .group_by(StockMovement.item_id)
        .order_by(StockMovement.item_id)
    ).all()
    return [(row[0], Decimal(row[1])) for row in rows]


def _build_movement(
    item: Item,
    lot: Lot | None,
    qty_delta: Decimal,
    movement_reason: MovementReason,
    from_location: StockLocation | None,
    to_location: StockLocation | None,
    ref_type: str | None,
    ref_id: str | None,
    moved_by: str | None,
    created_by: str | None,
    comment: str | None,
) -> StockMovement:
    return StockMovement(
        item_id=item.id,
        lot_id=lot.id if lot else None,
        qty_delta=qty_delta,
        unit_id=item.unit_id,
        unit_code_snapshot=item.unit.code,
        movement_reason_id=movement_reason.id,
        movement_reason_code_snapshot=movement_reason.code,
        from_location_id=from_location.id if from_location else None,
        from_location_code_snapshot=from_location.code if from_location else None,
        to_location_id=to_location.id if to_location else None,
        to_location_code_snapshot=to_location.code if to_location else None,
        ref_type=ref_type,
        ref_id=ref_id,
        moved_by=moved_by,
        created_by=created_by,
        comment=comment,
    )


def _get_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise InventoryValidationError("Item not found.")
    return item


def _get_lot(db: Session, lot_id: int | None) -> Lot:
    if lot_id is None:
        raise InventoryValidationError("Lot is required.")
    lot = db.get(Lot, lot_id)
    if not lot:
        raise InventoryValidationError("Lot not found.")
    return lot


def _get_reason(db: Session, movement_reason_id: int) -> MovementReason:
    reason = db.get(MovementReason, movement_reason_id)
    if not reason:
        raise InventoryValidationError("Movement reason not found.")
    return reason


def _get_location(db: Session, location_id: int | None) -> StockLocation | None:
    if location_id is None:
        return None
    location = db.get(StockLocation, location_id)
    if not location:
        raise InventoryValidationError("Stock location not found.")
    return location


def _enforce_reason_sign(reason: MovementReason, qty_delta: Decimal) -> None:
    sign = MovementReasonSign.POSITIVE if qty_delta > 0 else MovementReasonSign.NEGATIVE
    if reason.allowed_sign not in (MovementReasonSign.BOTH, sign):
        raise InventoryValidationError("Movement reason does not allow this sign.")


def _resolve_material_class_id(db: Session, item: Item, explicit_id: int | None) -> int | None:
    if explicit_id is not None:
        if not db.get(MaterialClass, explicit_id):
            raise InventoryValidationError("Material class not found.")
        return explicit_id
    blank = db.get(ItemBlank, item.id)
    if blank:
        return blank.material_class_id
    cartridge = db.get(ItemIvobaseCartridge, item.id)
    if cartridge:
        return cartridge.material_class_id
    return None


def _resolve_shade_id(db: Session, item: Item, explicit_id: int | None) -> int | None:
    if explicit_id is not None:
        if not db.get(Shade, explicit_id):
            raise InventoryValidationError("Shade not found.")
        return explicit_id
    blank = db.get(ItemBlank, item.id)
    if blank:
        return blank.shade_id
    cartridge = db.get(ItemIvobaseCartridge, item.id)
    if cartridge:
        return cartridge.shade_id
    return None


def _lookup_code(db: Session, model, row_id: int | None) -> str | None:
    if row_id is None:
        return None
    row = db.get(model, row_id)
    return row.code if row else None


def _build_instance_sku(item_sku: str, lot_code: str) -> str:
    return f"{item_sku}:{lot_code.strip()}"


def _resolve_manufacturer_id(db: Session, item: Item, explicit_id: int | None) -> int | None:
    manufacturer_id = explicit_id if explicit_id is not None else item.manufacturer_id
    if manufacturer_id is not None and not db.get(Manufacturer, manufacturer_id):
        raise InventoryValidationError("Manufacturer not found.")
    return manufacturer_id
