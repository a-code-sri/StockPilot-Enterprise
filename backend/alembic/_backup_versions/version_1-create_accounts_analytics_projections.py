"""create accounts analytics projections

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
        "accounts_daily_totals",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("income", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("expenses", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_accounts_daily_totals_day", "accounts_daily_totals", ["day"])

    op.create_table(
        "accounts_daily_category_totals",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("day", "category", "transaction_type", name="pk_accounts_daily_category_totals"),
    )
    op.create_index("ix_accounts_daily_category_totals_day", "accounts_daily_category_totals", ["day"])
    op.create_index("ix_accounts_daily_category_totals_category", "accounts_daily_category_totals", ["category"])
    op.create_index("ix_accounts_daily_category_totals_type", "accounts_daily_category_totals", ["transaction_type"])


def downgrade() -> None:
    op.drop_index("ix_accounts_daily_category_totals_type", table_name="accounts_daily_category_totals")
    op.drop_index("ix_accounts_daily_category_totals_category", table_name="accounts_daily_category_totals")
    op.drop_index("ix_accounts_daily_category_totals_day", table_name="accounts_daily_category_totals")
    op.drop_table("accounts_daily_category_totals")

    op.drop_index("ix_accounts_daily_totals_day", table_name="accounts_daily_totals")
    op.drop_table("accounts_daily_totals")