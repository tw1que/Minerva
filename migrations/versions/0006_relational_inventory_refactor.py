"""relational inventory and traceability refactor

Revision ID: 0006_relational_inventory_refactor
Revises: 0005_item_manufacturer
Create Date: 2026-05-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006_relational_inventory_refactor"
down_revision = "0005_item_manufacturer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    movement_reason_sign = sa.Enum(
        "positive",
        "negative",
        "both",
        name="movement_reason_sign",
    )
    movement_reason_sign.create(bind, checkfirst=True)

    op.create_table(
        "shade_systems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "material_classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "units_of_measure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "stock_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "movement_reasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("allowed_sign", movement_reason_sign, nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "shades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shade_system_id", sa.Integer(), sa.ForeignKey("shade_systems.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("shade_system_id", "code", name="uq_shade_system_code"),
    )
    op.create_index("ix_shades_shade_system_id", "shades", ["shade_system_id"])

    op.add_column("item_templates", sa.Column("item_type", sa.String(), nullable=True))
    op.add_column("item_templates", sa.Column("display_pattern", sa.String(), nullable=True))
    op.add_column(
        "item_templates",
        sa.Column("form_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_unique_constraint("uq_item_templates_item_type", "item_templates", ["item_type"])

    op.add_column("items", sa.Column("item_type", sa.String(), nullable=True))
    op.add_column("items", sa.Column("unit_id", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("sku", sa.String(), nullable=True))
    op.add_column("items", sa.Column("name", sa.String(), nullable=True))
    op.add_column(
        "items",
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_items_item_type", "items", ["item_type"])
    op.create_index("ix_items_sku", "items", ["sku"])
    op.create_index("ix_items_unit_id", "items", ["unit_id"])
    op.create_foreign_key("fk_items_unit_id", "items", "units_of_measure", ["unit_id"], ["id"], ondelete="SET NULL")

    op.execute("UPDATE items SET sku = product_code WHERE sku IS NULL")
    op.execute("UPDATE items SET name = COALESCE(product_code, sku) WHERE name IS NULL")
    op.alter_column("items", "sku", nullable=False)
    op.create_unique_constraint("uq_items_sku", "items", ["sku"])

    op.create_table(
        "item_blanks",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("diameter_mm", sa.Numeric(12, 3), nullable=False),
        sa.Column("thickness_mm", sa.Numeric(12, 3), nullable=False),
        sa.Column("shade_id", sa.Integer(), sa.ForeignKey("shades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_class_id", sa.Integer(), sa.ForeignKey("material_classes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_multilayer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("diameter_mm > 0", name="ck_item_blanks_diameter_positive"),
        sa.CheckConstraint("thickness_mm > 0", name="ck_item_blanks_thickness_positive"),
    )
    op.create_index("ix_item_blanks_shade_id", "item_blanks", ["shade_id"])
    op.create_index("ix_item_blanks_material_class_id", "item_blanks", ["material_class_id"])

    op.create_table(
        "item_ivobase_cartridges",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("shade_id", sa.Integer(), sa.ForeignKey("shades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_class_id", sa.Integer(), sa.ForeignKey("material_classes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("size_code", sa.String(), nullable=False),
    )
    op.create_index("ix_item_ivobase_cartridges_shade_id", "item_ivobase_cartridges", ["shade_id"])
    op.create_index("ix_item_ivobase_cartridges_material_class_id", "item_ivobase_cartridges", ["material_class_id"])

    op.add_column("lots", sa.Column("manufacturer_id", sa.Integer(), nullable=True))
    op.add_column("lots", sa.Column("material_class_id", sa.Integer(), nullable=True))
    op.add_column("lots", sa.Column("shade_id", sa.Integer(), nullable=True))
    op.add_column("lots", sa.Column("manufacturer_lot_code", sa.String(), nullable=True))
    op.add_column("lots", sa.Column("manufacturer_code_snapshot", sa.String(), nullable=True))
    op.add_column("lots", sa.Column("material_class_code_snapshot", sa.String(), nullable=True))
    op.add_column("lots", sa.Column("shade_code_snapshot", sa.String(), nullable=True))
    op.add_column("lots", sa.Column("item_sku_snapshot", sa.String(), nullable=True))
    op.add_column("lots", sa.Column("item_name_snapshot", sa.String(), nullable=True))
    op.create_index("ix_lots_manufacturer_id", "lots", ["manufacturer_id"])
    op.create_index("ix_lots_material_class_id", "lots", ["material_class_id"])
    op.create_index("ix_lots_shade_id", "lots", ["shade_id"])
    op.create_foreign_key("fk_lots_manufacturer_id", "lots", "manufacturers", ["manufacturer_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_lots_material_class_id", "lots", "material_classes", ["material_class_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_lots_shade_id", "lots", "shades", ["shade_id"], ["id"], ondelete="SET NULL")
    op.execute(
        """
        UPDATE lots
        SET manufacturer_id = items.manufacturer_id,
            manufacturer_lot_code = lots.lot_code,
            item_sku_snapshot = items.sku,
            item_name_snapshot = COALESCE(items.name, items.sku)
        FROM items
        WHERE lots.item_id = items.id
        """
    )
    op.execute(
        """
        UPDATE lots
        SET manufacturer_code_snapshot = manufacturers.code
        FROM manufacturers
        WHERE lots.manufacturer_id = manufacturers.id
        """
    )

    op.add_column("stock_movements", sa.Column("unit_id", sa.Integer(), nullable=True))
    op.add_column("stock_movements", sa.Column("unit_code_snapshot", sa.String(), nullable=True))
    op.add_column("stock_movements", sa.Column("movement_reason_id", sa.Integer(), nullable=True))
    op.add_column("stock_movements", sa.Column("movement_reason_code_snapshot", sa.String(), nullable=True))
    op.add_column("stock_movements", sa.Column("from_location_id", sa.Integer(), nullable=True))
    op.add_column("stock_movements", sa.Column("from_location_code_snapshot", sa.String(), nullable=True))
    op.add_column("stock_movements", sa.Column("to_location_id", sa.Integer(), nullable=True))
    op.add_column("stock_movements", sa.Column("to_location_code_snapshot", sa.String(), nullable=True))
    op.create_index("ix_stock_movements_unit_id", "stock_movements", ["unit_id"])
    op.create_index("ix_stock_movements_movement_reason_id", "stock_movements", ["movement_reason_id"])
    op.create_index("ix_stock_movements_from_location_id", "stock_movements", ["from_location_id"])
    op.create_index("ix_stock_movements_to_location_id", "stock_movements", ["to_location_id"])
    op.create_foreign_key("fk_stock_movements_unit_id", "stock_movements", "units_of_measure", ["unit_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_stock_movements_movement_reason_id", "stock_movements", "movement_reasons", ["movement_reason_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_stock_movements_from_location_id", "stock_movements", "stock_locations", ["from_location_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_stock_movements_to_location_id", "stock_movements", "stock_locations", ["to_location_id"], ["id"], ondelete="SET NULL")

    op.add_column("order_materials", sa.Column("unit_id", sa.Integer(), nullable=True))
    op.add_column("order_materials", sa.Column("unit_code_snapshot", sa.String(), nullable=True))
    op.add_column("order_materials", sa.Column("item_sku_snapshot", sa.String(), nullable=True))
    op.add_column("order_materials", sa.Column("item_name_snapshot", sa.String(), nullable=True))
    op.add_column("order_materials", sa.Column("lot_code_snapshot", sa.String(), nullable=True))
    op.add_column("order_materials", sa.Column("material_class_code_snapshot", sa.String(), nullable=True))
    op.add_column("order_materials", sa.Column("shade_code_snapshot", sa.String(), nullable=True))
    op.create_index("ix_order_materials_unit_id", "order_materials", ["unit_id"])
    op.create_foreign_key("fk_order_materials_unit_id", "order_materials", "units_of_measure", ["unit_id"], ["id"], ondelete="SET NULL")

    op.bulk_insert(
        sa.table(
            "units_of_measure",
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
            sa.column("active", sa.Boolean()),
        ),
        [
            {"code": "pcs", "name": "Pieces", "active": True},
            {"code": "disc", "name": "Disc", "active": True},
            {"code": "ml", "name": "Millilitre", "active": True},
            {"code": "g", "name": "Gram", "active": True},
        ],
    )
    op.bulk_insert(
        sa.table(
            "movement_reasons",
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
            sa.column("allowed_sign", movement_reason_sign),
            sa.column("active", sa.Boolean()),
        ),
        [
            {"code": "RECEIPT", "name": "receipt", "allowed_sign": "positive", "active": True},
            {"code": "CONSUME", "name": "consume", "allowed_sign": "negative", "active": True},
            {"code": "ADJUST", "name": "adjustment", "allowed_sign": "both", "active": True},
            {"code": "RETURN", "name": "return", "allowed_sign": "positive", "active": True},
            {"code": "SCRAP", "name": "scrap", "allowed_sign": "negative", "active": True},
            {"code": "TRANSFER", "name": "transfer", "allowed_sign": "both", "active": True},
        ],
    )
    op.bulk_insert(
        sa.table(
            "material_classes",
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
            sa.column("active", sa.Boolean()),
        ),
        [
            {"code": "PMMA", "name": "PMMA", "active": True},
            {"code": "ZIRCONIA", "name": "Zirconia", "active": True},
            {"code": "PEEK", "name": "PEEK", "active": True},
            {"code": "COMPOSITE", "name": "Composite", "active": True},
        ],
    )
    op.execute(
        """
        INSERT INTO shade_systems (name, active)
        VALUES ('VITA Classical', true), ('VITA 3D-Master', true)
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO shades (shade_system_id, code, active)
        SELECT ss.id, shade.code, true
        FROM shade_systems ss
        JOIN (
            VALUES
                ('VITA Classical', 'A1'),
                ('VITA Classical', 'A2'),
                ('VITA Classical', 'A3'),
                ('VITA Classical', 'B1'),
                ('VITA Classical', 'BL2'),
                ('VITA 3D-Master', '2M2')
        ) AS shade(system_name, code)
            ON shade.system_name = ss.name
        ON CONFLICT ON CONSTRAINT uq_shade_system_code DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE items
        SET unit_id = u.id
        FROM units_of_measure u
        WHERE items.uom = u.code AND items.unit_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE stock_movements
        SET unit_id = u.id,
            unit_code_snapshot = COALESCE(stock_movements.uom, u.code)
        FROM units_of_measure u
        WHERE stock_movements.uom = u.code
        """
    )
    op.execute(
        """
        UPDATE stock_movements
        SET unit_code_snapshot = COALESCE(unit_code_snapshot, uom),
            movement_reason_code_snapshot = reason::text
        """
    )
    op.execute(
        """
        UPDATE stock_movements
        SET movement_reason_id = mr.id
        FROM movement_reasons mr
        WHERE stock_movements.movement_reason_code_snapshot = mr.code
        """
    )
    op.execute(
        """
        UPDATE order_materials
        SET item_sku_snapshot = items.sku,
            item_name_snapshot = COALESCE(items.name, items.sku),
            lot_code_snapshot = COALESCE(lots.manufacturer_lot_code, lots.lot_code),
            material_class_code_snapshot = lots.material_class_code_snapshot,
            shade_code_snapshot = lots.shade_code_snapshot
        FROM items, lots
        WHERE order_materials.item_id = items.id
          AND order_materials.lot_id = lots.id
        """
    )
    op.execute(
        """
        UPDATE order_materials
        SET unit_id = sm.unit_id,
            unit_code_snapshot = sm.unit_code_snapshot
        FROM stock_movements sm
        WHERE order_materials.stock_movement_id = sm.id
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW stock_balance AS
        SELECT
            lot_id,
            SUM(qty_delta) AS quantity_on_hand
        FROM stock_movements
        GROUP BY lot_id
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS stock_balance")

    op.drop_constraint("fk_order_materials_unit_id", "order_materials", type_="foreignkey")
    op.drop_index("ix_order_materials_unit_id", table_name="order_materials")
    op.drop_column("order_materials", "shade_code_snapshot")
    op.drop_column("order_materials", "material_class_code_snapshot")
    op.drop_column("order_materials", "lot_code_snapshot")
    op.drop_column("order_materials", "item_name_snapshot")
    op.drop_column("order_materials", "item_sku_snapshot")
    op.drop_column("order_materials", "unit_code_snapshot")
    op.drop_column("order_materials", "unit_id")

    op.drop_constraint("fk_stock_movements_to_location_id", "stock_movements", type_="foreignkey")
    op.drop_constraint("fk_stock_movements_from_location_id", "stock_movements", type_="foreignkey")
    op.drop_constraint("fk_stock_movements_movement_reason_id", "stock_movements", type_="foreignkey")
    op.drop_constraint("fk_stock_movements_unit_id", "stock_movements", type_="foreignkey")
    op.drop_index("ix_stock_movements_to_location_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_from_location_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_movement_reason_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_unit_id", table_name="stock_movements")
    op.drop_column("stock_movements", "to_location_code_snapshot")
    op.drop_column("stock_movements", "to_location_id")
    op.drop_column("stock_movements", "from_location_code_snapshot")
    op.drop_column("stock_movements", "from_location_id")
    op.drop_column("stock_movements", "movement_reason_code_snapshot")
    op.drop_column("stock_movements", "movement_reason_id")
    op.drop_column("stock_movements", "unit_code_snapshot")
    op.drop_column("stock_movements", "unit_id")

    op.drop_constraint("fk_lots_shade_id", "lots", type_="foreignkey")
    op.drop_constraint("fk_lots_material_class_id", "lots", type_="foreignkey")
    op.drop_constraint("fk_lots_manufacturer_id", "lots", type_="foreignkey")
    op.drop_index("ix_lots_shade_id", table_name="lots")
    op.drop_index("ix_lots_material_class_id", table_name="lots")
    op.drop_index("ix_lots_manufacturer_id", table_name="lots")
    op.drop_column("lots", "item_name_snapshot")
    op.drop_column("lots", "item_sku_snapshot")
    op.drop_column("lots", "shade_code_snapshot")
    op.drop_column("lots", "material_class_code_snapshot")
    op.drop_column("lots", "manufacturer_code_snapshot")
    op.drop_column("lots", "manufacturer_lot_code")
    op.drop_column("lots", "shade_id")
    op.drop_column("lots", "material_class_id")
    op.drop_column("lots", "manufacturer_id")

    op.drop_index("ix_item_ivobase_cartridges_material_class_id", table_name="item_ivobase_cartridges")
    op.drop_index("ix_item_ivobase_cartridges_shade_id", table_name="item_ivobase_cartridges")
    op.drop_table("item_ivobase_cartridges")
    op.drop_index("ix_item_blanks_material_class_id", table_name="item_blanks")
    op.drop_index("ix_item_blanks_shade_id", table_name="item_blanks")
    op.drop_table("item_blanks")

    op.drop_constraint("uq_items_sku", "items", type_="unique")
    op.drop_constraint("fk_items_unit_id", "items", type_="foreignkey")
    op.drop_index("ix_items_unit_id", table_name="items")
    op.drop_index("ix_items_sku", table_name="items")
    op.drop_index("ix_items_item_type", table_name="items")
    op.drop_column("items", "metadata")
    op.drop_column("items", "name")
    op.drop_column("items", "sku")
    op.drop_column("items", "unit_id")
    op.drop_column("items", "item_type")

    op.drop_constraint("uq_item_templates_item_type", "item_templates", type_="unique")
    op.drop_column("item_templates", "form_config")
    op.drop_column("item_templates", "display_pattern")
    op.drop_column("item_templates", "item_type")

    op.drop_index("ix_shades_shade_system_id", table_name="shades")
    op.drop_table("shades")
    op.drop_table("movement_reasons")
    op.drop_table("stock_locations")
    op.drop_table("units_of_measure")
    op.drop_table("material_classes")
    op.drop_table("shade_systems")

    movement_reason_sign = sa.Enum(
        "positive",
        "negative",
        "both",
        name="movement_reason_sign",
    )
    movement_reason_sign.drop(op.get_bind(), checkfirst=True)
