"""move manufacturer to items

Revision ID: 0005_item_manufacturer
Revises: 0004_product_code_instance_seq
Create Date: 2026-01-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_item_manufacturer"
down_revision = "0004_product_code_instance_seq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("manufacturer_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_items_manufacturer_id", "items", ["manufacturer_id"])
    op.create_foreign_key(
        "fk_items_manufacturer_id",
        "items",
        "manufacturers",
        ["manufacturer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE items
        SET manufacturer_id = item_templates.manufacturer_id
        FROM item_templates
        WHERE items.template_id = item_templates.id
        """
    )

    op.drop_constraint(
        "item_templates_manufacturer_id_fkey",
        "item_templates",
        type_="foreignkey",
    )
    op.drop_column("item_templates", "manufacturer_id")


def downgrade() -> None:
    op.add_column(
        "item_templates",
        sa.Column("manufacturer_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "item_templates_manufacturer_id_fkey",
        "item_templates",
        "manufacturers",
        ["manufacturer_id"],
        ["id"],
    )

    op.execute(
        """
        UPDATE item_templates
        SET manufacturer_id = picked.manufacturer_id
        FROM (
            SELECT template_id, MIN(manufacturer_id) AS manufacturer_id
            FROM items
            WHERE manufacturer_id IS NOT NULL
            GROUP BY template_id
        ) AS picked
        WHERE item_templates.id = picked.template_id
        """
    )

    op.drop_constraint("fk_items_manufacturer_id", "items", type_="foreignkey")
    op.drop_index("ix_items_manufacturer_id", table_name="items")
    op.drop_column("items", "manufacturer_id")
