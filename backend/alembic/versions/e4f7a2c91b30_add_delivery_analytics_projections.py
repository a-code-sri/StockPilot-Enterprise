"""add delivery analytics projections

Revision ID: e4f7a2c91b30
Revises: d968c2f705f0
Create Date: 2026-10-20

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4f7a2c91b30"
down_revision = "d968c2f705f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_daily_status_counts",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "day",
            "status",
            name="uq_delivery_daily_status_day_status",
        ),
    )

    op.create_index(
        "ix_delivery_daily_status_day",
        "delivery_daily_status_counts",
        ["day"],
    )

    op.create_index(
        "ix_delivery_daily_status_status",
        "delivery_daily_status_counts",
        ["status"],
    )

    op.create_table(
        "delivery_daily_item_counts",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "day",
            "product_name",
            name="uq_delivery_daily_item_day_product",
        ),
    )

    op.create_index(
        "ix_delivery_daily_item_day",
        "delivery_daily_item_counts",
        ["day"],
    )

    op.create_index(
        "ix_delivery_daily_item_product",
        "delivery_daily_item_counts",
        ["product_name"],
    )

    op.create_table(
        "delivery_daily_hour_counts",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column(
            "count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "day",
            "hour",
            name="uq_delivery_daily_hour_day_hour",
        ),
    )

    op.create_index(
        "ix_delivery_daily_hour_day",
        "delivery_daily_hour_counts",
        ["day"],
    )

    op.create_index(
        "ix_delivery_daily_hour_hour",
        "delivery_daily_hour_counts",
        ["hour"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_delivery_daily_hour_hour",
        table_name="delivery_daily_hour_counts",
    )
    op.drop_index(
        "ix_delivery_daily_hour_day",
        table_name="delivery_daily_hour_counts",
    )
    op.drop_table("delivery_daily_hour_counts")

    op.drop_index(
        "ix_delivery_daily_item_product",
        table_name="delivery_daily_item_counts",
    )
    op.drop_index(
        "ix_delivery_daily_item_day",
        table_name="delivery_daily_item_counts",
    )
    op.drop_table("delivery_daily_item_counts")

    op.drop_index(
        "ix_delivery_daily_status_status",
        table_name="delivery_daily_status_counts",
    )
    op.drop_index(
        "ix_delivery_daily_status_day",
        table_name="delivery_daily_status_counts",
    )
    op.drop_table("delivery_daily_status_counts")