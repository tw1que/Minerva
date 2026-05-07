"""auth and orders

Revision ID: 0002_auth_orders
Revises: 0001_initial
Create Date: 2026-01-08 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_auth_orders"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = postgresql.ENUM("ADMIN", "OPERATOR", "VIEWER", name="user_role", create_type=False)
    order_status = postgresql.ENUM(
        "DRAFT",
        "RESERVED",
        "ALLOCATED",
        "FULFILLED",
        "CANCELLED",
        name="order_status",
        create_type=False,
    )

    postgresql.ENUM("ADMIN", "OPERATOR", "VIEWER", name="user_role").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "DRAFT",
        "RESERVED",
        "ALLOCATED",
        "FULFILLED",
        "CANCELLED",
        name="order_status",
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
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
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_number", sa.String(), nullable=False, unique=True),
        sa.Column("status", order_status, server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
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
    )

    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("qty_requested", sa.Numeric(12, 3), nullable=False),
        sa.Column("qty_allocated", sa.Numeric(12, 3), server_default=sa.text("0"), nullable=False),
        sa.Column("uom", sa.String(), nullable=False),
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
        sa.UniqueConstraint("order_id", "item_id", name="uq_order_line_item"),
        sa.CheckConstraint("qty_requested > 0", name="ck_order_line_qty_positive"),
        sa.CheckConstraint("qty_allocated >= 0", name="ck_order_line_allocated_nonneg"),
        sa.CheckConstraint("qty_allocated <= qty_requested", name="ck_order_line_allocated_leq"),
    )

    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"])
    op.create_index("ix_order_lines_item_id", "order_lines", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_order_lines_item_id", table_name="order_lines")
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_table("orders")
    op.drop_table("users")

    order_status = sa.Enum(
        "DRAFT",
        "RESERVED",
        "ALLOCATED",
        "FULFILLED",
        "CANCELLED",
        name="order_status",
    )
    user_role = sa.Enum("ADMIN", "OPERATOR", "VIEWER", name="user_role")

    order_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
