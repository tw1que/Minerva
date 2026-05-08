"""Initial Minerva core schema.

Revision ID: 0001_core
Revises:
Create Date: 2026-05-08 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_core"
down_revision = None
branch_labels = None
depends_on = None


movement_reason_sign = postgresql.ENUM(
    "positive",
    "negative",
    "both",
    name="movement_reason_sign",
    create_type=False,
)
user_role = postgresql.ENUM(
    "ADMIN",
    "OPERATOR",
    "VIEWER",
    name="user_role",
    create_type=False,
)
order_status = postgresql.ENUM(
    "DRAFT",
    "OPEN",
    "COMPLETED",
    "CANCELLED",
    name="order_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    movement_reason_sign.create(bind, checkfirst=False)
    user_role.create(bind, checkfirst=False)
    order_status.create(bind, checkfirst=False)

    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "shade_systems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "material_classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "units_of_measure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "stock_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "movement_reasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("allowed_sign", movement_reason_sign, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "shades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shade_system_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["shade_system_id"], ["shade_systems.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("shade_system_id", "code", name="uq_shades_system_code"),
    )
    op.create_index(op.f("ix_shades_shade_system_id"), "shades", ["shade_system_id"], unique=False)

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("manufacturer_id", sa.Integer(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units_of_measure.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index(op.f("ix_items_item_type"), "items", ["item_type"], unique=False)
    op.create_index(op.f("ix_items_manufacturer_id"), "items", ["manufacturer_id"], unique=False)
    op.create_index(op.f("ix_items_sku"), "items", ["sku"], unique=False)
    op.create_index(op.f("ix_items_unit_id"), "items", ["unit_id"], unique=False)

    op.create_table(
        "item_blanks",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("diameter_mm", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("thickness_mm", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("shade_id", sa.Integer(), nullable=True),
        sa.Column("material_class_id", sa.Integer(), nullable=False),
        sa.Column("is_multilayer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("diameter_mm > 0", name="ck_item_blanks_diameter_positive"),
        sa.CheckConstraint("thickness_mm > 0", name="ck_item_blanks_thickness_positive"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_class_id"], ["material_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shade_id"], ["shades.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index(op.f("ix_item_blanks_material_class_id"), "item_blanks", ["material_class_id"], unique=False)
    op.create_index(op.f("ix_item_blanks_shade_id"), "item_blanks", ["shade_id"], unique=False)

    op.create_table(
        "item_ivobase_cartridges",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("shade_id", sa.Integer(), nullable=True),
        sa.Column("material_class_id", sa.Integer(), nullable=False),
        sa.Column("size_code", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_class_id"], ["material_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shade_id"], ["shades.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index(
        op.f("ix_item_ivobase_cartridges_material_class_id"),
        "item_ivobase_cartridges",
        ["material_class_id"],
        unique=False,
    )
    op.create_index(op.f("ix_item_ivobase_cartridges_shade_id"), "item_ivobase_cartridges", ["shade_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_number", sa.String(length=255), nullable=False),
        sa.Column("status", order_status, nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("order_number"),
    )

    op.create_table(
        "lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("manufacturer_id", sa.Integer(), nullable=True),
        sa.Column("material_class_id", sa.Integer(), nullable=True),
        sa.Column("shade_id", sa.Integer(), nullable=True),
        sa.Column("manufacturer_lot_code", sa.String(length=255), nullable=True),
        sa.Column("lot_code", sa.String(length=255), nullable=False),
        sa.Column("instance_sku", sa.String(length=255), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_ref", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("item_sku_snapshot", sa.String(length=255), nullable=False),
        sa.Column("item_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("manufacturer_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("material_class_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("shade_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["material_class_id"], ["material_classes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shade_id"], ["shades.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("instance_sku"),
        sa.UniqueConstraint("item_id", "lot_code", name="uq_lots_item_lot_code"),
    )
    op.create_index(op.f("ix_lots_item_id"), "lots", ["item_id"], unique=False)
    op.create_index(op.f("ix_lots_manufacturer_id"), "lots", ["manufacturer_id"], unique=False)
    op.create_index(op.f("ix_lots_material_class_id"), "lots", ["material_class_id"], unique=False)
    op.create_index(op.f("ix_lots_shade_id"), "lots", ["shade_id"], unique=False)

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("lot_id", sa.Integer(), nullable=True),
        sa.Column("qty_delta", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("unit_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("movement_reason_id", sa.Integer(), nullable=False),
        sa.Column("movement_reason_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("from_location_id", sa.Integer(), nullable=True),
        sa.Column("from_location_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("to_location_id", sa.Integer(), nullable=True),
        sa.Column("to_location_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("ref_type", sa.String(length=64), nullable=True),
        sa.Column("ref_id", sa.String(length=255), nullable=True),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("moved_by", sa.String(length=128), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.CheckConstraint("qty_delta <> 0", name="ck_stock_movements_qty_delta_nonzero"),
        sa.ForeignKeyConstraint(["from_location_id"], ["stock_locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["movement_reason_id"], ["movement_reasons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_location_id"], ["stock_locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units_of_measure.id"], ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_stock_movements_from_location_id"), "stock_movements", ["from_location_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_item_id"), "stock_movements", ["item_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_lot_id"), "stock_movements", ["lot_id"], unique=False)
    op.create_index(
        op.f("ix_stock_movements_movement_reason_id"),
        "stock_movements",
        ["movement_reason_id"],
        unique=False,
    )
    op.create_index(op.f("ix_stock_movements_to_location_id"), "stock_movements", ["to_location_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_unit_id"), "stock_movements", ["unit_id"], unique=False)

    op.create_table(
        "order_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("lot_id", sa.Integer(), nullable=False),
        sa.Column("qty_used", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("unit_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("item_sku_snapshot", sa.String(length=255), nullable=False),
        sa.Column("item_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("lot_code_snapshot", sa.String(length=255), nullable=False),
        sa.Column("material_class_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("shade_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("stock_movement_id", sa.Integer(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("used_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint("qty_used > 0", name="ck_order_materials_qty_used_positive"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_movement_id"], ["stock_movements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units_of_measure.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("stock_movement_id"),
    )
    op.create_index(op.f("ix_order_materials_item_id"), "order_materials", ["item_id"], unique=False)
    op.create_index(op.f("ix_order_materials_lot_id"), "order_materials", ["lot_id"], unique=False)
    op.create_index(op.f("ix_order_materials_order_id"), "order_materials", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_materials_unit_id"), "order_materials", ["unit_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_order_materials_unit_id"), table_name="order_materials")
    op.drop_index(op.f("ix_order_materials_order_id"), table_name="order_materials")
    op.drop_index(op.f("ix_order_materials_lot_id"), table_name="order_materials")
    op.drop_index(op.f("ix_order_materials_item_id"), table_name="order_materials")
    op.drop_table("order_materials")

    op.drop_index(op.f("ix_stock_movements_unit_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_to_location_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_movement_reason_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_lot_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_item_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_from_location_id"), table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index(op.f("ix_lots_shade_id"), table_name="lots")
    op.drop_index(op.f("ix_lots_material_class_id"), table_name="lots")
    op.drop_index(op.f("ix_lots_manufacturer_id"), table_name="lots")
    op.drop_index(op.f("ix_lots_item_id"), table_name="lots")
    op.drop_table("lots")

    op.drop_table("orders")

    op.drop_index(op.f("ix_item_ivobase_cartridges_shade_id"), table_name="item_ivobase_cartridges")
    op.drop_index(op.f("ix_item_ivobase_cartridges_material_class_id"), table_name="item_ivobase_cartridges")
    op.drop_table("item_ivobase_cartridges")

    op.drop_index(op.f("ix_item_blanks_shade_id"), table_name="item_blanks")
    op.drop_index(op.f("ix_item_blanks_material_class_id"), table_name="item_blanks")
    op.drop_table("item_blanks")

    op.drop_index(op.f("ix_items_unit_id"), table_name="items")
    op.drop_index(op.f("ix_items_sku"), table_name="items")
    op.drop_index(op.f("ix_items_manufacturer_id"), table_name="items")
    op.drop_index(op.f("ix_items_item_type"), table_name="items")
    op.drop_table("items")

    op.drop_index(op.f("ix_shades_shade_system_id"), table_name="shades")
    op.drop_table("shades")

    op.drop_table("users")
    op.drop_table("movement_reasons")
    op.drop_table("stock_locations")
    op.drop_table("units_of_measure")
    op.drop_table("material_classes")
    op.drop_table("shade_systems")
    op.drop_table("manufacturers")

    bind = op.get_bind()
    order_status.drop(bind, checkfirst=False)
    user_role.drop(bind, checkfirst=False)
    movement_reason_sign.drop(bind, checkfirst=False)
