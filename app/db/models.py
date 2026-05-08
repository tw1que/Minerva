from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


JSON_VARIANT = JSON().with_variant(JSONB, "postgresql")


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
    OPEN = "OPEN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Manufacturer(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class ShadeSystem(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "shade_systems"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Shade(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "shades"

    id: Mapped[int] = mapped_column(primary_key=True)
    shade_system_id: Mapped[int] = mapped_column(
        ForeignKey("shade_systems.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    shade_system: Mapped[ShadeSystem] = relationship()

    __table_args__ = (
        UniqueConstraint("shade_system_id", "code", name="uq_shades_system_code"),
    )


class MaterialClass(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "material_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class UnitOfMeasure(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "units_of_measure"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class StockLocation(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "stock_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class MovementReason(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "movement_reasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_sign: Mapped[MovementReasonSign] = mapped_column(
        Enum(MovementReasonSign, name="movement_reason_sign"),
        nullable=False,
    )


class User(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)


class Item(Base, TimestampMixin, SoftActiveMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer_id: Mapped[int | None] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        index=True,
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units_of_measure.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_VARIANT,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    manufacturer: Mapped[Manufacturer | None] = relationship()
    unit: Mapped[UnitOfMeasure] = relationship()
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
    is_multilayer: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

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
    size_code: Mapped[str] = mapped_column(String(64), nullable=False)

    item: Mapped[Item] = relationship(back_populates="ivobase_cartridge_details")
    shade: Mapped[Shade | None] = relationship()
    material_class: Mapped[MaterialClass] = relationship()


class Lot(Base, TimestampMixin):
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
    manufacturer_lot_code: Mapped[str | None] = mapped_column(String(255))
    lot_code: Mapped[str] = mapped_column(String(255), nullable=False)
    instance_sku: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    certificate_ref: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    item_sku_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    item_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer_code_snapshot: Mapped[str | None] = mapped_column(String(64))
    material_class_code_snapshot: Mapped[str | None] = mapped_column(String(64))
    shade_code_snapshot: Mapped[str | None] = mapped_column(String(64))

    item: Mapped[Item] = relationship()
    manufacturer: Mapped[Manufacturer | None] = relationship()
    material_class: Mapped[MaterialClass | None] = relationship()
    shade: Mapped[Shade | None] = relationship()

    __table_args__ = (
        UniqueConstraint("item_id", "lot_code", name="uq_lots_item_lot_code"),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
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
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units_of_measure.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    unit_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    movement_reason_id: Mapped[int] = mapped_column(
        ForeignKey("movement_reasons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    movement_reason_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    from_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        index=True,
    )
    from_location_code_snapshot: Mapped[str | None] = mapped_column(String(64))
    to_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        index=True,
    )
    to_location_code_snapshot: Mapped[str | None] = mapped_column(String(64))
    ref_type: Mapped[str | None] = mapped_column(String(64))
    ref_id: Mapped[str | None] = mapped_column(String(255))
    moved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    moved_by: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[str | None] = mapped_column(String(128))
    comment: Mapped[str | None] = mapped_column(Text)

    item: Mapped[Item] = relationship()
    lot: Mapped[Lot | None] = relationship()
    unit: Mapped[UnitOfMeasure] = relationship()
    movement_reason: Mapped[MovementReason] = relationship()
    from_location: Mapped[StockLocation | None] = relationship(foreign_keys=[from_location_id])
    to_location: Mapped[StockLocation | None] = relationship(foreign_keys=[to_location_id])

    __table_args__ = (
        CheckConstraint("qty_delta <> 0", name="ck_stock_movements_qty_delta_nonzero"),
    )


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        nullable=False,
        server_default=OrderStatus.DRAFT.name,
    )
    notes: Mapped[str | None] = mapped_column(Text)


class OrderMaterial(Base):
    __tablename__ = "order_materials"

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
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    qty_used: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units_of_measure.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    unit_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    item_sku_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    item_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    lot_code_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    material_class_code_snapshot: Mapped[str | None] = mapped_column(String(64))
    shade_code_snapshot: Mapped[str | None] = mapped_column(String(64))
    stock_movement_id: Mapped[int] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    used_by: Mapped[str | None] = mapped_column(String(128))

    order: Mapped[Order] = relationship()
    item: Mapped[Item] = relationship()
    lot: Mapped[Lot] = relationship()
    unit: Mapped[UnitOfMeasure] = relationship()
    stock_movement: Mapped[StockMovement] = relationship()

    __table_args__ = (
        CheckConstraint("qty_used > 0", name="ck_order_materials_qty_used_positive"),
    )
