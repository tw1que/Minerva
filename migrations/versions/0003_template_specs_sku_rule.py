"""template specs and sku rules

Revision ID: 0003_template_specs_sku_rule
Revises: 0002_auth_orders
Create Date: 2026-01-08 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_template_specs_sku_rule"
down_revision = "0002_auth_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "item_templates",
        sa.Column(
            "attribute_specs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "item_templates",
        sa.Column(
            "sku_rule",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column("items", sa.Column("sku_rule_version", sa.Integer(), nullable=True))
    op.alter_column(
        "items",
        "attributes_hash",
        new_column_name="attribute_hash",
        existing_type=sa.String(),
    )
    op.create_index("ix_items_attribute_hash", "items", ["attribute_hash"])
    op.create_index("ix_items_sku", "items", ["sku"])


def downgrade() -> None:
    op.drop_index("ix_items_sku", table_name="items")
    op.drop_index("ix_items_attribute_hash", table_name="items")
    op.alter_column(
        "items",
        "attribute_hash",
        new_column_name="attributes_hash",
        existing_type=sa.String(),
    )
    op.drop_column("items", "sku_rule_version")

    op.drop_column("item_templates", "sku_rule")
    op.drop_column("item_templates", "attribute_specs")
