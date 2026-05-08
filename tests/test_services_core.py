from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Item,
    ItemBlank,
    ItemIvobaseCartridge,
    Lot,
    Manufacturer,
    MaterialClass,
    MovementReason,
    Order,
    OrderMaterial,
    OrderStatus,
    Shade,
    ShadeSystem,
    StockLocation,
    StockMovement,
    UnitOfMeasure,
)
from app.services.inventory import (
    AdjustStockInput,
    ConsumeStockInput,
    InsufficientStockError,
    InventoryValidationError,
    ReceiveStockInput,
    adjust_stock,
    consume_stock,
    list_item_balances,
    list_lot_balances,
    receive_stock,
)
from app.services.items import (
    CreateBlankItemInput,
    CreateItemInput,
    CreateIvobaseCartridgeItemInput,
    create_blank_item,
    create_item,
    create_ivobase_cartridge_item,
)


def _lookup_by_code(db: Session, model, code: str):
    return db.execute(select(model).where(model.code == code)).scalar_one()


def test_reference_bootstrap_creates_core_lookups(bootstrapped_db: Session) -> None:
    unit_codes = {row.code for row in bootstrapped_db.execute(select(UnitOfMeasure)).scalars()}
    material_class_codes = {row.code for row in bootstrapped_db.execute(select(MaterialClass)).scalars()}
    movement_reason_codes = {row.code for row in bootstrapped_db.execute(select(MovementReason)).scalars()}
    shade_system = _lookup_by_code(bootstrapped_db, ShadeSystem, "VITA_CLASSICAL")
    shade_codes = {
        row.code
        for row in bootstrapped_db.execute(select(Shade).where(Shade.shade_system_id == shade_system.id)).scalars()
    }

    assert {"disc", "pcs", "ml", "g"} <= unit_codes
    assert {"ZIRCONIA", "PMMA", "PEEK"} <= material_class_codes
    assert {"RECEIPT", "CONSUME", "ADJUST", "RETURN", "SCRAP", "TRANSFER"} <= movement_reason_codes
    assert {"A1", "A2", "A3", "B1", "BL2"} <= shade_codes


def test_create_item_creates_generic_item(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "pcs")
    manufacturer = _lookup_by_code(bootstrapped_db, Manufacturer, "GENERIC")

    item = create_item(
        bootstrapped_db,
        CreateItemInput(
            sku="GEN-001",
            name="Generic Item",
            item_type="generic",
            unit_id=unit.id,
            manufacturer_id=manufacturer.id,
        ),
    )

    stored = bootstrapped_db.get(Item, item.id)
    assert stored is not None
    assert stored.sku == "GEN-001"
    assert stored.manufacturer_id == manufacturer.id
    assert stored.unit_id == unit.id


def test_create_blank_item_creates_item_and_details(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "disc")
    manufacturer = _lookup_by_code(bootstrapped_db, Manufacturer, "GENERIC")
    material_class = _lookup_by_code(bootstrapped_db, MaterialClass, "ZIRCONIA")
    shade = _lookup_by_code(bootstrapped_db, Shade, "A1")

    item = create_blank_item(
        bootstrapped_db,
        CreateBlankItemInput(
            sku="BLANK-001",
            name="Blank Item",
            item_type="blank",
            unit_id=unit.id,
            manufacturer_id=manufacturer.id,
            diameter_mm=Decimal("98.500"),
            thickness_mm=Decimal("14.000"),
            material_class_id=material_class.id,
            shade_id=shade.id,
            is_multilayer=True,
        ),
    )

    details = bootstrapped_db.get(ItemBlank, item.id)
    assert details is not None
    assert details.material_class_id == material_class.id
    assert details.shade_id == shade.id
    assert details.is_multilayer is True


def test_create_ivobase_cartridge_item_creates_item_and_details(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "pcs")
    manufacturer = _lookup_by_code(bootstrapped_db, Manufacturer, "GENERIC")
    material_class = _lookup_by_code(bootstrapped_db, MaterialClass, "PMMA")
    shade = _lookup_by_code(bootstrapped_db, Shade, "A2")

    item = create_ivobase_cartridge_item(
        bootstrapped_db,
        CreateIvobaseCartridgeItemInput(
            sku="IVO-001",
            name="Ivobase Cartridge",
            item_type="ivobase_cartridge",
            unit_id=unit.id,
            manufacturer_id=manufacturer.id,
            material_class_id=material_class.id,
            shade_id=shade.id,
            size_code="50G",
        ),
    )

    details = bootstrapped_db.get(ItemIvobaseCartridge, item.id)
    assert details is not None
    assert details.material_class_id == material_class.id
    assert details.shade_id == shade.id
    assert details.size_code == "50G"


def test_receive_stock_creates_lot_movement_and_snapshots(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "pcs")
    manufacturer = _lookup_by_code(bootstrapped_db, Manufacturer, "GENERIC")
    material_class = _lookup_by_code(bootstrapped_db, MaterialClass, "ZIRCONIA")
    shade = _lookup_by_code(bootstrapped_db, Shade, "A1")
    location = _lookup_by_code(bootstrapped_db, StockLocation, "MAIN")
    reason = _lookup_by_code(bootstrapped_db, MovementReason, "RECEIPT")
    item = create_item(
        bootstrapped_db,
        CreateItemInput(
            sku="STOCK-001",
            name="Stock Item",
            item_type="generic",
            unit_id=unit.id,
            manufacturer_id=manufacturer.id,
        ),
    )

    lot, movement = receive_stock(
        bootstrapped_db,
        ReceiveStockInput(
            item_id=item.id,
            quantity=Decimal("5.000"),
            movement_reason_id=reason.id,
            manufacturer_lot_code="MLOT-001",
            manufacturer_id=manufacturer.id,
            material_class_id=material_class.id,
            shade_id=shade.id,
            lot_code="LOT-001",
            to_location_id=location.id,
            comment="Initial receipt",
        ),
    )

    stored_lot = bootstrapped_db.get(Lot, lot.id)
    stored_movement = bootstrapped_db.get(StockMovement, movement.id)
    lot_balances = dict(list_lot_balances(bootstrapped_db))
    item_balances = dict(list_item_balances(bootstrapped_db))

    assert stored_lot is not None
    assert stored_movement is not None
    assert stored_movement.qty_delta == Decimal("5.000")
    assert stored_movement.lot_id == stored_lot.id
    assert stored_lot.item_sku_snapshot == "STOCK-001"
    assert stored_lot.item_name_snapshot == "Stock Item"
    assert stored_lot.manufacturer_code_snapshot == "GENERIC"
    assert stored_lot.material_class_code_snapshot == "ZIRCONIA"
    assert stored_lot.shade_code_snapshot == "A1"
    assert stored_movement.unit_code_snapshot == "pcs"
    assert stored_movement.movement_reason_code_snapshot == "RECEIPT"
    assert stored_movement.from_location_code_snapshot is None
    assert stored_movement.to_location_code_snapshot == "MAIN"
    assert lot_balances[stored_lot.id] == Decimal("5.000")
    assert item_balances[item.id] == Decimal("5.000")


def test_adjust_stock_requires_comment(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "pcs")
    item = create_item(
        bootstrapped_db,
        CreateItemInput(
            sku="ADJ-001",
            name="Adjust Item",
            item_type="generic",
            unit_id=unit.id,
        ),
    )
    reason = _lookup_by_code(bootstrapped_db, MovementReason, "ADJUST")

    with pytest.raises(InventoryValidationError, match="comment is required"):
        adjust_stock(
            bootstrapped_db,
            AdjustStockInput(
                item_id=item.id,
                qty_delta=Decimal("1.000"),
                movement_reason_id=reason.id,
                comment="   ",
            ),
        )


def test_adjust_stock_rejects_zero_delta(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "pcs")
    item = create_item(
        bootstrapped_db,
        CreateItemInput(
            sku="ADJ-002",
            name="Zero Adjust Item",
            item_type="generic",
            unit_id=unit.id,
        ),
    )
    reason = _lookup_by_code(bootstrapped_db, MovementReason, "ADJUST")

    with pytest.raises(InventoryValidationError, match="qty_delta must not be zero"):
        adjust_stock(
            bootstrapped_db,
            AdjustStockInput(
                item_id=item.id,
                qty_delta=Decimal("0"),
                movement_reason_id=reason.id,
                comment="Manual correction",
            ),
        )


def test_movement_reason_rejects_wrong_direction(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "pcs")
    item = create_item(
        bootstrapped_db,
        CreateItemInput(
            sku="SIGN-001",
            name="Direction Test Item",
            item_type="generic",
            unit_id=unit.id,
        ),
    )
    wrong_reason = _lookup_by_code(bootstrapped_db, MovementReason, "CONSUME")

    with pytest.raises(InventoryValidationError, match="does not allow this sign"):
        receive_stock(
            bootstrapped_db,
            ReceiveStockInput(
                item_id=item.id,
                quantity=Decimal("1.000"),
                movement_reason_id=wrong_reason.id,
                manufacturer_lot_code="BAD-LOT-001",
            ),
        )


def test_consume_stock_creates_traceable_order_material_and_reduces_balance(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "disc")
    manufacturer = _lookup_by_code(bootstrapped_db, Manufacturer, "GENERIC")
    material_class = _lookup_by_code(bootstrapped_db, MaterialClass, "ZIRCONIA")
    shade = _lookup_by_code(bootstrapped_db, Shade, "A1")
    receipt_reason = _lookup_by_code(bootstrapped_db, MovementReason, "RECEIPT")
    consume_reason = _lookup_by_code(bootstrapped_db, MovementReason, "CONSUME")
    item = create_blank_item(
        bootstrapped_db,
        CreateBlankItemInput(
            sku="CONS-001",
            name="Consumable Blank",
            item_type="blank",
            unit_id=unit.id,
            manufacturer_id=manufacturer.id,
            diameter_mm=Decimal("98.500"),
            thickness_mm=Decimal("14.000"),
            material_class_id=material_class.id,
            shade_id=shade.id,
        ),
    )
    order = Order(order_number="ORD-001", status=OrderStatus.OPEN)
    bootstrapped_db.add(order)
    bootstrapped_db.commit()
    bootstrapped_db.refresh(order)

    lot, _ = receive_stock(
        bootstrapped_db,
        ReceiveStockInput(
            item_id=item.id,
            quantity=Decimal("5.000"),
            movement_reason_id=receipt_reason.id,
            manufacturer_lot_code="MLOT-CONS-001",
            manufacturer_id=manufacturer.id,
            material_class_id=material_class.id,
            shade_id=shade.id,
            lot_code="LOT-CONS-001",
        ),
    )

    movement, order_material = consume_stock(
        bootstrapped_db,
        ConsumeStockInput(
            order_id=order.id,
            item_id=item.id,
            lot_id=lot.id,
            quantity=Decimal("2.000"),
            movement_reason_id=consume_reason.id,
            used_by="tech-1",
        ),
    )

    stored_movement = bootstrapped_db.get(StockMovement, movement.id)
    stored_order_material = bootstrapped_db.get(OrderMaterial, order_material.id)
    lot_balances = dict(list_lot_balances(bootstrapped_db))
    item_balances = dict(list_item_balances(bootstrapped_db))

    assert stored_movement is not None
    assert stored_order_material is not None
    assert stored_movement.qty_delta == Decimal("-2.000")
    assert stored_order_material.stock_movement_id == stored_movement.id
    assert stored_order_material.order_id == order.id
    assert stored_order_material.item_id == item.id
    assert stored_order_material.lot_id == lot.id
    assert stored_order_material.unit_code_snapshot == "disc"
    assert stored_order_material.item_sku_snapshot == "CONS-001"
    assert stored_order_material.item_name_snapshot == "Consumable Blank"
    assert stored_order_material.lot_code_snapshot == "LOT-CONS-001"
    assert stored_order_material.material_class_code_snapshot == "ZIRCONIA"
    assert stored_order_material.shade_code_snapshot == "A1"
    assert lot_balances[lot.id] == Decimal("3.000")
    assert item_balances[item.id] == Decimal("3.000")


def test_consume_stock_rejects_overconsumption(bootstrapped_db: Session) -> None:
    unit = _lookup_by_code(bootstrapped_db, UnitOfMeasure, "pcs")
    receipt_reason = _lookup_by_code(bootstrapped_db, MovementReason, "RECEIPT")
    consume_reason = _lookup_by_code(bootstrapped_db, MovementReason, "CONSUME")
    item = create_item(
        bootstrapped_db,
        CreateItemInput(
            sku="CONS-OVER-001",
            name="Overconsume Item",
            item_type="generic",
            unit_id=unit.id,
        ),
    )
    order = Order(order_number="ORD-OVER-001", status=OrderStatus.OPEN)
    bootstrapped_db.add(order)
    bootstrapped_db.commit()
    bootstrapped_db.refresh(order)

    lot, _ = receive_stock(
        bootstrapped_db,
        ReceiveStockInput(
            item_id=item.id,
            quantity=Decimal("1.000"),
            movement_reason_id=receipt_reason.id,
            manufacturer_lot_code="OVER-LOT-001",
        ),
    )

    with pytest.raises(InsufficientStockError, match="Cannot consume more than current lot balance"):
        consume_stock(
            bootstrapped_db,
            ConsumeStockInput(
                order_id=order.id,
                item_id=item.id,
                lot_id=lot.id,
                quantity=Decimal("2.000"),
                movement_reason_id=consume_reason.id,
            ),
        )
