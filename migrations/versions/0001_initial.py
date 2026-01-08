"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-08 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    sku_sequence_scope = sa.Enum(
        "GLOBAL",
        "PER_TEMPLATE",
        "PER_PREFIX",
        "PER_YEAR",
        name="sku_sequence_scope",
    )
    template_field_type = sa.Enum(
        "TEXT",
        "INT",
        "DECIMAL",
        "ENUM",
        name="template_field_type",
    )
    stock_reason = sa.Enum(
        "RECEIPT",
        "CONSUME",
        "ADJUST",
        "RETURN",
        "SCRAP",
        "TRANSFER",
        name="stock_reason",
    )

    sku_sequence_scope.create(op.get_bind(), checkfirst=True)
    template_field_type.create(op.get_bind(), checkfirst=True)
    stock_reason.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    op.create_table(
        "item_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("manufacturer_id", sa.Integer(), sa.ForeignKey("manufacturers.id")),
        sa.Column("sku_prefix", sa.String(), nullable=False),
        sa.Column("sku_pattern", sa.String(), nullable=False),
        sa.Column("seq_scope", sku_sequence_scope, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    op.create_table(
        "template_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("item_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(), nullable=False),
        sa.Column("field_type", template_field_type, nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("include_in_sku", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sku_order", sa.Integer()),
        sa.Column("default_value", sa.String()),
        sa.Column("enum_values", postgresql.JSONB()),
        sa.Column("format", sa.String()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("template_id", "field_key", name="uq_template_field_key"),
    )
    op.create_index("ix_template_fields_template_id", "template_fields", ["template_id"])

    op.create_table(
        "sku_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("item_templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("scope_key", sa.String(), nullable=False),
        sa.Column("next_seq", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("template_id", "scope_key", name="uq_counter_scope"),
    )
    op.create_index("ix_sku_counters_template_id", "sku_counters", ["template_id"])

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("item_templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(), nullable=False, unique=True),
        sa.Column("uom", sa.String(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), nullable=False),
        sa.Column("attributes_hash", sa.String(), nullable=False),
        sa.Column("track_lots", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("template_id", "attributes_hash", name="uq_item_variant"),
    )
    op.create_index("ix_items_template_id", "items", ["template_id"])

    op.create_table(
        "lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("lot_code", sa.String(), nullable=False),
        sa.Column("supplier_name", sa.String()),
        sa.Column("manufacturing_date", sa.DateTime(timezone=True)),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("certificate_ref", sa.String()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("item_id", "lot_code", name="uq_lot_per_item"),
        sa.CheckConstraint(
            "(expires_at IS NULL OR manufacturing_date IS NULL OR expires_at > manufacturing_date)",
            name="ck_lot_expiry_after_mfg",
        ),
    )
    op.create_index("ix_lots_item_id", "lots", ["item_id"])

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id", ondelete="RESTRICT")),
        sa.Column("qty_delta", sa.Numeric(12, 3), nullable=False),
        sa.Column("uom", sa.String(), nullable=False),
        sa.Column("reason", stock_reason, nullable=False),
        sa.Column("ref_type", sa.String()),
        sa.Column("ref_id", sa.String()),
        sa.Column("created_by", sa.String()),
        sa.Column("comment", sa.Text()),
        sa.CheckConstraint("qty_delta <> 0", name="ck_stock_qty_not_zero"),
    )
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])
    op.create_index("ix_stock_movements_item_id", "stock_movements", ["item_id"])
    op.create_index("ix_stock_movements_lot_id", "stock_movements", ["lot_id"])

    op.create_table(
        "order_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "lot_id",
            sa.Integer(),
            sa.ForeignKey("lots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("qty_used", sa.Numeric(12, 3), nullable=False),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("used_by", sa.String()),
        sa.Column(
            "stock_movement_id",
            sa.Integer(),
            sa.ForeignKey("stock_movements.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
    )
    op.create_index("ix_order_materials_order_id", "order_materials", ["order_id"])
    op.create_index("ix_order_materials_item_id", "order_materials", ["item_id"])
    op.create_index("ix_order_materials_lot_id", "order_materials", ["lot_id"])


def downgrade() -> None:
    op.drop_index("ix_order_materials_lot_id", table_name="order_materials")
    op.drop_index("ix_order_materials_item_id", table_name="order_materials")
    op.drop_index("ix_order_materials_order_id", table_name="order_materials")
    op.drop_table("order_materials")

    op.drop_index("ix_stock_movements_lot_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_item_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_created_at", table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index("ix_lots_item_id", table_name="lots")
    op.drop_table("lots")

    op.drop_index("ix_items_template_id", table_name="items")
    op.drop_table("items")

    op.drop_index("ix_sku_counters_template_id", table_name="sku_counters")
    op.drop_table("sku_counters")

    op.drop_index("ix_template_fields_template_id", table_name="template_fields")
    op.drop_table("template_fields")

    op.drop_table("item_templates")
    op.drop_table("manufacturers")

    stock_reason = sa.Enum(
        "RECEIPT",
        "CONSUME",
        "ADJUST",
        "RETURN",
        "SCRAP",
        "TRANSFER",
        name="stock_reason",
    )
    template_field_type = sa.Enum(
        "TEXT",
        "INT",
        "DECIMAL",
        "ENUM",
        name="template_field_type",
    )
    sku_sequence_scope = sa.Enum(
        "GLOBAL",
        "PER_TEMPLATE",
        "PER_PREFIX",
        "PER_YEAR",
        name="sku_sequence_scope",
    )

    stock_reason.drop(op.get_bind(), checkfirst=True)
    template_field_type.drop(op.get_bind(), checkfirst=True)
    sku_sequence_scope.drop(op.get_bind(), checkfirst=True)
