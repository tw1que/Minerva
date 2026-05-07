from __future__ import annotations

from decimal import Decimal

import pytest

from app.db.models import (
    Item,
    ItemBlank,
    Lot,
    Manufacturer,
    MaterialClass,
    MovementReason,
    MovementReasonSign,
    OrderMaterial,
    Shade,
    StockMovement,
    UnitOfMeasure,
)
from app.services import inventory as inventory_service
from app.services import items as items_service
from app.services.inventory import (
    ConsumeStockCommand,
    InsufficientStockError,
    MovementReasonValidationError,
    ReceiveStockCommand,
    _enforce_reason_sign,
    consume_stock,
    create_lot_snapshot,
    get_stock_balance_rows,
    receive_stock,
)
from app.services.items import ItemBlankPayload, create_relational_item


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def all(self):
        return self.value


class FakeSession:
    def __init__(self, objects: dict[tuple[type, int], object] | None = None) -> None:
        self.objects = objects or {}
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False
        self.refreshed: list[object] = []
        self.begin_called = False

    def get(self, model, pk):
        return self.objects.get((model, pk))

    def add(self, obj) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, obj) -> None:
        self.refreshed.append(obj)

    def rollback(self) -> None:
        self.rolled_back = True

    def flush(self) -> None:
        return None

    def execute(self, _stmt):
        return FakeScalarResult(None)

    def in_transaction(self) -> bool:
        return True

    def begin(self):
        self.begin_called = True
        raise AssertionError("inventory services should not call db.begin()")


def test_lookup_models_have_expected_constraints() -> None:
    constraints = {constraint.name: constraint for constraint in ItemBlank.__table__.constraints}
    assert "ck_item_blanks_diameter_positive" in constraints
    assert "ck_item_blanks_thickness_positive" in constraints

    qty_constraints = {constraint.name for constraint in StockMovement.__table__.constraints}
    assert "ck_stock_qty_not_zero" in qty_constraints


def test_create_relational_item_with_blank_details(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession(
        {
            (UnitOfMeasure, 1): UnitOfMeasure(id=1, code="disc", name="Disc"),
            (MaterialClass, 2): MaterialClass(id=2, code="ZIRCONIA", name="Zirconia"),
            (Shade, 3): Shade(id=3, shade_system_id=1, code="A2"),
        }
    )
    monkeypatch.setattr(items_service, "get_item_by_sku", lambda *_: None)

    item = create_relational_item(
        db,
        item_type="blank",
        sku="BLK-98-20-A2",
        name="Blank 98/20 A2",
        unit_id=1,
        blank_details=ItemBlankPayload(
            diameter_mm=Decimal("98"),
            thickness_mm=Decimal("20"),
            material_class_id=2,
            shade_id=3,
            is_multilayer=False,
        ),
    )

    assert item.sku == "BLK-98-20-A2"
    assert item.uom == "disc"
    assert item.blank_details is not None
    assert item.blank_details.material_class_id == 2
    assert item.attributes == {}
    assert item.attribute_hash is None
    assert db.committed is True


def test_create_lot_snapshot_fills_snapshot_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    item = Item(id=10, sku="BLK-98-20-A2", name="Blank", item_type="blank")
    manufacturer = Manufacturer(id=1, code="IVO", name="Ivoclar")
    material_class = MaterialClass(id=2, code="ZIRCONIA", name="Zirconia")
    shade = Shade(id=3, shade_system_id=1, code="A2")
    db = FakeSession(
        {
            (Manufacturer, 1): manufacturer,
            (MaterialClass, 2): material_class,
            (Shade, 3): shade,
        }
    )

    monkeypatch.setattr(inventory_service, "assign_instance_seq", lambda *_: 4)
    monkeypatch.setattr(inventory_service, "build_instance_sku", lambda sku, seq: f"{sku}-{seq:04d}")

    lot = create_lot_snapshot(
        db,
        item=item,
        manufacturer_lot_code="LOT-42",
        manufacturer_id=1,
        material_class_id=2,
        shade_id=3,
    )

    assert lot.lot_code == "LOT-42"
    assert lot.manufacturer_lot_code == "LOT-42"
    assert lot.item_sku_snapshot == "BLK-98-20-A2"
    assert lot.item_name_snapshot == "Blank"
    assert lot.material_class_code_snapshot == "ZIRCONIA"
    assert lot.shade_code_snapshot == "A2"


def test_receive_stock_creates_positive_stock_movement(monkeypatch: pytest.MonkeyPatch) -> None:
    item = Item(id=10, sku="BLK-98-20-A2", name="Blank", item_type="blank")
    lot = Lot(id=20, item_id=10, lot_code="LOT-42", seq=1, instance_sku="BLK-98-20-A2-0001")
    movement = StockMovement(id=30, item_id=10, lot_id=20, qty_delta=Decimal("5"))
    db = FakeSession({(Item, 10): item})

    monkeypatch.setattr(inventory_service, "create_lot_snapshot", lambda *_, **__: lot)
    monkeypatch.setattr(inventory_service, "_build_movement", lambda *_, **__: movement)

    created_lot, created_movement = receive_stock(
        db,
        ReceiveStockCommand(item_id=10, quantity=Decimal("5"), manufacturer_lot_code="LOT-42"),
    )

    assert created_lot is lot
    assert created_movement.qty_delta == Decimal("5")
    assert db.committed is True
    assert db.begin_called is False


def test_consume_stock_creates_order_material_and_negative_movement(monkeypatch: pytest.MonkeyPatch) -> None:
    item = Item(id=10, sku="BLK-98-20-A2", name="Blank", item_type="blank")
    lot = Lot(
        id=20,
        item_id=10,
        lot_code="LOT-42",
        manufacturer_lot_code="LOT-42",
        seq=1,
        instance_sku="BLK-98-20-A2-0001",
        item_sku_snapshot="BLK-98-20-A2",
        item_name_snapshot="Blank",
        material_class_code_snapshot="ZIRCONIA",
        shade_code_snapshot="A2",
    )
    movement = StockMovement(
        id=30,
        item_id=10,
        lot_id=20,
        qty_delta=Decimal("-2"),
        unit_id=1,
        unit_code_snapshot="disc",
    )
    db = FakeSession({(Item, 10): item, (Lot, 20): lot})

    monkeypatch.setattr(inventory_service, "get_lot_on_hand_qty", lambda *_: Decimal("3"))
    monkeypatch.setattr(inventory_service, "_build_movement", lambda *_, **__: movement)

    order_material, stock_movement = consume_stock(
        db,
        ConsumeStockCommand(order_id="CASE-1", item_id=10, lot_id=20, quantity=Decimal("2")),
    )

    assert stock_movement.qty_delta == Decimal("-2")
    assert order_material.qty_used == Decimal("2")
    assert order_material.item_sku_snapshot == "BLK-98-20-A2"
    assert order_material.shade_code_snapshot == "A2"
    assert db.committed is True
    assert db.begin_called is False

    lot.item_sku_snapshot = "CHANGED"
    assert order_material.item_sku_snapshot == "BLK-98-20-A2"


def test_consume_stock_checks_available_quantity(monkeypatch: pytest.MonkeyPatch) -> None:
    item = Item(id=10, sku="BLK-98-20-A2", item_type="blank")
    lot = Lot(id=20, item_id=10, lot_code="LOT-42", seq=1, instance_sku="X")
    db = FakeSession({(Item, 10): item, (Lot, 20): lot})

    monkeypatch.setattr(inventory_service, "get_lot_on_hand_qty", lambda *_: Decimal("1"))

    with pytest.raises(InsufficientStockError):
        consume_stock(
            db,
            ConsumeStockCommand(order_id="CASE-1", item_id=10, lot_id=20, quantity=Decimal("2")),
        )


def test_get_stock_balance_rows_uses_sum_projection() -> None:
    db = FakeSession()
    db.execute = lambda _stmt: FakeScalarResult([(1, Decimal("5")), (2, Decimal("-1"))])  # type: ignore[method-assign]

    balances = get_stock_balance_rows(db)

    assert balances == [(1, Decimal("5")), (2, Decimal("-1"))]


def test_receive_stock_rolls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    item = Item(id=10, sku="BLK-98-20-A2", name="Blank", item_type="blank")
    db = FakeSession({(Item, 10): item})

    monkeypatch.setattr(
        inventory_service,
        "create_lot_snapshot",
        lambda *_, **__: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError):
        receive_stock(
            db,
            ReceiveStockCommand(item_id=10, quantity=Decimal("5"), manufacturer_lot_code="LOT-42"),
        )

    assert db.rolled_back is True


def test_movement_reason_allowed_sign_enforced() -> None:
    positive_reason = MovementReason(code="RECEIPT", name="receipt", allowed_sign=MovementReasonSign.POSITIVE)
    negative_reason = MovementReason(code="CONSUME", name="consume", allowed_sign=MovementReasonSign.NEGATIVE)

    with pytest.raises(MovementReasonValidationError):
        _enforce_reason_sign(positive_reason, Decimal("-1"))
    with pytest.raises(MovementReasonValidationError):
        _enforce_reason_sign(negative_reason, Decimal("1"))
