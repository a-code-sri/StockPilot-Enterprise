"""create inventory analytics projections

Revision ID: <PUT_REVISION_ID_HERE>
Revises: <PUT_DOWN_REVISION_ID_HERE>
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa

revision = "<PUT_REVISION_ID_HERE>"
down_revision = "<PUT_DOWN_REVISION_ID_HERE>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_daily_consumption",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("consumed_qty", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_inventory_daily_consumption_day", "inventory_daily_consumption", ["day"])

    op.create_table(
        "inventory_monthly_orders",
        sa.Column("month", sa.Date(), primary_key=True),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_inventory_monthly_orders_month", "inventory_monthly_orders", ["month"])

    op.create_table(
        "inventory_alerts_snapshot",
        sa.Column("snapshot_date", sa.Date(), primary_key=True),
        sa.Column("dead_stock_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("near_expiry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reorder_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_inventory_alerts_snapshot_date", "inventory_alerts_snapshot", ["snapshot_date"])


def downgrade() -> None:
    op.drop_index("ix_inventory_alerts_snapshot_date", table_name="inventory_alerts_snapshot")
    op.drop_table("inventory_alerts_snapshot")

    op.drop_index("ix_inventory_monthly_orders_month", table_name="inventory_monthly_orders")
    op.drop_table("inventory_monthly_orders")

    op.drop_index("ix_inventory_daily_consumption_day", table_name="inventory_daily_consumption")
    op.drop_table("inventory_daily_consumption")