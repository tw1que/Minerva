"""product code and instance sequencing

Revision ID: 0004_product_code_instance_seq
Revises: 0003_template_specs_sku_rule
Create Date: 2026-01-08 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_product_code_instance_seq"
down_revision = "0003_template_specs_sku_rule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "items",
        "sku",
        new_column_name="product_code",
        existing_type=sa.String(),
        existing_nullable=False,
    )
    op.drop_index("ix_items_sku", table_name="items")
    op.drop_constraint("items_sku_key", "items", type_="unique")
    op.create_index("ix_items_product_code", "items", ["product_code"])
    op.create_unique_constraint(
        "uq_item_product_code",
        "items",
        ["template_id", "product_code"],
    )

    op.add_column("lots", sa.Column("seq", sa.Integer(), nullable=True))
    op.add_column("lots", sa.Column("instance_sku", sa.String(), nullable=True))
    op.create_index("ix_lots_seq", "lots", ["seq"])
    op.create_index("ix_lots_instance_sku", "lots", ["instance_sku"])

    op.execute(
        """
        UPDATE lots
        SET seq = ordered.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY received_at, id) AS rn
            FROM lots
        ) AS ordered
        WHERE lots.id = ordered.id
        """
    )
    op.execute(
        """
        UPDATE lots
        SET instance_sku = items.product_code || '-' || lpad(lots.seq::text, 4, '0')
        FROM items
        WHERE lots.item_id = items.id
        """
    )

    op.alter_column("lots", "seq", nullable=False)
    op.alter_column("lots", "instance_sku", nullable=False)
    op.create_unique_constraint("uq_lot_item_seq", "lots", ["item_id", "seq"])
    op.create_unique_constraint("uq_lot_instance_sku", "lots", ["instance_sku"])


def downgrade() -> None:
    op.drop_constraint("uq_lot_instance_sku", "lots", type_="unique")
    op.drop_constraint("uq_lot_item_seq", "lots", type_="unique")
    op.drop_index("ix_lots_instance_sku", table_name="lots")
    op.drop_index("ix_lots_seq", table_name="lots")
    op.drop_column("lots", "instance_sku")
    op.drop_column("lots", "seq")

    op.drop_constraint("uq_item_product_code", "items", type_="unique")
    op.drop_index("ix_items_product_code", table_name="items")
    op.alter_column(
        "items",
        "product_code",
        new_column_name="sku",
        existing_type=sa.String(),
        existing_nullable=False,
    )
    op.create_index("ix_items_sku", "items", ["sku"])
    op.create_unique_constraint("items_sku_key", "items", ["sku"])
