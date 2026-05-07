from __future__ import annotations

import enum
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, synonym


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now(),
    )


class SoftActiveMixin:
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class SKUSequenceScope(enum.Enum):
    GLOBAL = "GLOBAL"
    PER_TEMPLATE = "PER_TEMPLATE"
    PER_PREFIX = "PER_PREFIX"
    PER_YEAR = "PER_YEAR"


class TemplateFieldType(enum.Enum):
    TEXT = "TEXT"
    INT = "INT"
    DECIMAL = "DECIMAL"
    ENUM = "ENUM"


class AttributeType(enum.Enum):
    ENUM = "enum"
    INT = "int"
    DECIMAL = "decimal"
    STRING = "string"
    BOOL = "bool"


class StockReason(enum.Enum):
    RECEIPT = "RECEIPT"
    CONSUME = "CONSUME"
    ADJUST = "ADJUST"
    RETURN = "RETURN"
    SCRAP = "SCRAP"
    TRANSFER = "TRANSFER"


class MovementReasonSign(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOTH = "both"


class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class OrderStatus(enum.Enum):
    DRAFT = "DRAFT"
    RESERVED = "RESERVED"
    ALLOCATED = "ALLOCATED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class Manufacturer(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<Manufacturer id={self.id} code={self.code!r} name={self.name!r}>"


class ShadeSystem(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "shade_systems"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class Shade(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "shades"

    id: Mapped[int] = mapped_column(primary_key=True)
    shade_system_id: Mapped[int] = mapped_column(
        ForeignKey("shade_systems.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String, nullable=False)

    shade_system: Mapped[ShadeSystem] = relationship()

    __table_args__ = (
        UniqueConstraint("shade_system_id", "code", name="uq_shade_system_code"),
    )


class MaterialClass(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "material_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class UnitOfMeasure(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "units_of_measure"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class StockLocation(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "stock_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class MovementReason(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "movement_reasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    allowed_sign: Mapped[MovementReasonSign] = mapped_column(
        Enum(MovementReasonSign, name="movement_reason_sign"),
        nullable=False,
    )


class User(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role.value}>"


class ItemTemplate(Base, TimestampMixin, SoftActiveMixin):
    """Template configuration for SKU rendering and UI, not item master-data truth."""

    __tablename__ = "item_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[str | None] = mapped_column(String, unique=True)

    sku_prefix: Mapped[str] = mapped_column(String, nullable=False)
    sku_pattern: Mapped[str] = mapped_column(String, nullable=False)
    seq_scope: Mapped[SKUSequenceScope] = mapped_column(
        Enum(SKUSequenceScope, name="sku_sequence_scope"),
        nullable=False,
    )
    display_pattern: Mapped[str | None] = mapped_column(String)
    form_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Legacy template-driven field definitions remain for compatibility and UI config.
    attribute_specs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    sku_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    fields: Mapped[list["TemplateField"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    items: Mapped[list["Item"]] = relationship(back_populates="template")

    def __repr__(self) -> str:
        return f"<ItemTemplate id={self.id} name={self.name!r} prefix={self.sku_prefix!r}>"


class TemplateField(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "template_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("item_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_key: Mapped[str] = mapped_column(String, nullable=False)
    field_type: Mapped[TemplateFieldType] = mapped_column(
        Enum(TemplateFieldType, name="template_field_type"),
        nullable=False,
    )

    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    include_in_sku: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sku_order: Mapped[int | None] = mapped_column(Integer)
    default_value: Mapped[str | None] = mapped_column(String)
    enum_values: Mapped[dict | None] = mapped_column(JSONB)
    format: Mapped[str | None] = mapped_column(String)

    template: Mapped[ItemTemplate] = relationship(back_populates="fields")

    __table_args__ = (
        UniqueConstraint("template_id", "field_key", name="uq_template_field_key"),
    )

    def __repr__(self) -> str:
        return f"<TemplateField id={self.id} template_id={self.template_id} key={self.field_key!r}>"


class SKUCounter(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "sku_counters"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("item_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    scope_key: Mapped[str] = mapped_column(String, nullable=False)
    next_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __table_args__ = (
        UniqueConstraint("template_id", "scope_key", name="uq_counter_scope"),
    )

    def __repr__(self) -> str:
        return (
            f"<SKUCounter id={self.id} template_id={self.template_id} "
            f"scope={self.scope_key!r} next={self.next_seq}>"
        )


class Item(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_type: Mapped[str | None] = mapped_column(String, index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_templates.id", ondelete="RESTRICT"),
        index=True,
    )
    manufacturer_id: Mapped[int | None] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        index=True,
    )
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units_of_measure.id", ondelete="SET NULL"),
        index=True,
    )

    sku: Mapped[str] = mapped_column("sku", String, nullable=False, unique=True, index=True)
    product_code = synonym("sku")

    name: Mapped[str | None] = mapped_column(String)

    # Legacy JSONB attributes remain only for migration compatibility.
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    attribute_hash: Mapped[str | None] = mapped_column(String, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    sku_rule_version: Mapped[int | None] = mapped_column(Integer)

    track_lots: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    uom: Mapped[str | None] = mapped_column(String)

    template: Mapped[ItemTemplate | None] = relationship(back_populates="items")
    manufacturer: Mapped[Manufacturer | None] = relationship()
    unit: Mapped[UnitOfMeasure | None] = relationship()
    blank_details: Mapped["ItemBlank | None"] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    ivobase_cartridge_details: Mapped["ItemIvobaseCartridge | None"] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    lots: Mapped[list["Lot"]] = relationship(back_populates="item")
    order_lines: Mapped[list["OrderLine"]] = relationship(back_populates="item")

    __table_args__ = (
        UniqueConstraint("template_id", "attribute_hash", name="uq_item_variant"),
    )

    @property
    def display_name(self) -> str:
        return self.name or self.sku

    def __repr__(self) -> str:
        return f"<Item id={self.id} sku={self.sku!r} item_type={self.item_type!r}>"


class ItemBlank(Base):
    __tablename__ = "item_blanks"

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    diameter_mm: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    thickness_mm: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    shade_id: Mapped[int | None] = mapped_column(
        ForeignKey("shades.id", ondelete="SET NULL"),
        index=True,
    )
    material_class_id: Mapped[int] = mapped_column(
        ForeignKey("material_classes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_multilayer: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    item: Mapped[Item] = relationship(back_populates="blank_details")
    shade: Mapped[Shade | None] = relationship()
    material_class: Mapped[MaterialClass] = relationship()

    __table_args__ = (
        CheckConstraint("diameter_mm > 0", name="ck_item_blanks_diameter_positive"),
        CheckConstraint("thickness_mm > 0", name="ck_item_blanks_thickness_positive"),
    )


class ItemIvobaseCartridge(Base):
    __tablename__ = "item_ivobase_cartridges"

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    shade_id: Mapped[int | None] = mapped_column(
        ForeignKey("shades.id", ondelete="SET NULL"),
        index=True,
    )
    material_class_id: Mapped[int] = mapped_column(
        ForeignKey("material_classes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    size_code: Mapped[str] = mapped_column(String, nullable=False)

    item: Mapped[Item] = relationship(back_populates="ivobase_cartridge_details")
    shade: Mapped[Shade | None] = relationship()
    material_class: Mapped[MaterialClass] = relationship()


class Lot(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    manufacturer_id: Mapped[int | None] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        index=True,
    )
    material_class_id: Mapped[int | None] = mapped_column(
        ForeignKey("material_classes.id", ondelete="SET NULL"),
        index=True,
    )
    shade_id: Mapped[int | None] = mapped_column(
        ForeignKey("shades.id", ondelete="SET NULL"),
        index=True,
    )

    manufacturer_lot_code: Mapped[str | None] = mapped_column(String)
    lot_code: Mapped[str] = mapped_column(String, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    instance_sku: Mapped[str] = mapped_column(String, nullable=False, index=True)

    supplier_name: Mapped[str | None] = mapped_column(String)
    manufacturing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    certificate_ref: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)

    manufacturer_code_snapshot: Mapped[str | None] = mapped_column(String)
    material_class_code_snapshot: Mapped[str | None] = mapped_column(String)
    shade_code_snapshot: Mapped[str | None] = mapped_column(String)
    item_sku_snapshot: Mapped[str | None] = mapped_column(String)
    item_name_snapshot: Mapped[str | None] = mapped_column(String)

    item: Mapped[Item] = relationship(back_populates="lots")
    manufacturer: Mapped[Manufacturer | None] = relationship()
    material_class: Mapped[MaterialClass | None] = relationship()
    shade: Mapped[Shade | None] = relationship()

    __table_args__ = (
        UniqueConstraint("item_id", "lot_code", name="uq_lot_per_item"),
        UniqueConstraint("item_id", "seq", name="uq_lot_item_seq"),
        UniqueConstraint("instance_sku", name="uq_lot_instance_sku"),
        CheckConstraint(
            "(expires_at IS NULL OR manufacturing_date IS NULL OR expires_at > manufacturing_date)",
            name="ck_lot_expiry_after_mfg",
        ),
    )

    def __repr__(self) -> str:
        return f"<Lot id={self.id} item_id={self.item_id} lot_code={self.lot_code!r}>"


class StockMovement(Base):
    """Append-only inventory ledger. Corrections must be new counter-movements."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"),
        index=True,
    )

    qty_delta: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units_of_measure.id", ondelete="SET NULL"),
        index=True,
    )
    unit_code_snapshot: Mapped[str | None] = mapped_column(String)
    uom: Mapped[str | None] = mapped_column(String)

    movement_reason_id: Mapped[int | None] = mapped_column(
        ForeignKey("movement_reasons.id", ondelete="SET NULL"),
        index=True,
    )
    movement_reason_code_snapshot: Mapped[str | None] = mapped_column(String)
    reason: Mapped[StockReason | None] = mapped_column(
        Enum(StockReason, name="stock_reason"),
    )

    from_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        index=True,
    )
    from_location_code_snapshot: Mapped[str | None] = mapped_column(String)
    to_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        index=True,
    )
    to_location_code_snapshot: Mapped[str | None] = mapped_column(String)

    ref_type: Mapped[str | None] = mapped_column(String)
    ref_id: Mapped[str | None] = mapped_column(String)
    created_by: Mapped[str | None] = mapped_column(String)
    comment: Mapped[str | None] = mapped_column(Text)

    item: Mapped[Item] = relationship()
    lot: Mapped[Lot | None] = relationship()
    unit: Mapped[UnitOfMeasure | None] = relationship()
    movement_reason: Mapped[MovementReason | None] = relationship()
    from_location: Mapped[StockLocation | None] = relationship(foreign_keys=[from_location_id])
    to_location: Mapped[StockLocation | None] = relationship(foreign_keys=[to_location_id])

    __table_args__ = (
        CheckConstraint("qty_delta <> 0", name="ck_stock_qty_not_zero"),
    )

    def __repr__(self) -> str:
        code = self.movement_reason_code_snapshot or (self.reason.value if self.reason else None)
        return f"<StockMovement id={self.id} item_id={self.item_id} lot_id={self.lot_id} qty={self.qty_delta} reason={code}>"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        nullable=False,
        server_default=OrderStatus.DRAFT.value,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_by: Mapped[User | None] = relationship()

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} number={self.order_number!r} status={self.status.value}>"


class OrderLine(Base, TimestampMixin):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    qty_requested: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    qty_allocated: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        server_default="0",
    )
    uom: Mapped[str] = mapped_column(String, nullable=False)

    order: Mapped[Order] = relationship(back_populates="lines")
    item: Mapped[Item] = relationship(back_populates="order_lines")

    __table_args__ = (
        CheckConstraint("qty_requested > 0", name="ck_order_line_qty_positive"),
        CheckConstraint("qty_allocated >= 0", name="ck_order_line_allocated_nonneg"),
        CheckConstraint("qty_allocated <= qty_requested", name="ck_order_line_allocated_leq"),
        UniqueConstraint("order_id", "item_id", name="uq_order_line_item"),
    )

    def __repr__(self) -> str:
        return f"<OrderLine id={self.id} order_id={self.order_id} item_id={self.item_id} qty={self.qty_requested}>"


class OrderMaterial(Base):
    __tablename__ = "order_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    qty_used: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units_of_measure.id", ondelete="SET NULL"),
        index=True,
    )
    unit_code_snapshot: Mapped[str | None] = mapped_column(String)
    item_sku_snapshot: Mapped[str | None] = mapped_column(String)
    item_name_snapshot: Mapped[str | None] = mapped_column(String)
    lot_code_snapshot: Mapped[str | None] = mapped_column(String)
    material_class_code_snapshot: Mapped[str | None] = mapped_column(String)
    shade_code_snapshot: Mapped[str | None] = mapped_column(String)

    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    used_by: Mapped[str | None] = mapped_column(String)

    stock_movement_id: Mapped[int] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    item: Mapped[Item] = relationship()
    lot: Mapped[Lot] = relationship()
    unit: Mapped[UnitOfMeasure | None] = relationship()
    stock_movement: Mapped[StockMovement] = relationship()

    def __repr__(self) -> str:
        return f"<OrderMaterial id={self.id} order_id={self.order_id!r} lot_id={self.lot_id} qty={self.qty_used}>"


def canonical_json(attrs: dict[str, Any]) -> str:
    return json.dumps(dict(sorted(attrs.items())), separators=(",", ":"), ensure_ascii=False)


def compute_attributes_hash(canonicalized_attrs: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(canonicalized_attrs).encode("utf-8")).hexdigest()
