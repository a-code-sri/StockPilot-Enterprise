"""create org analytics projections

Revision ID: <PUT_REVISION_ID_HERE>
Revises: <PUT_DOWN_REVISION_ID_HERE>
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "<PUT_REVISION_ID_HERE>"
down_revision = "<PUT_DOWN_REVISION_ID_HERE>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_overview_snapshot",
        sa.Column("histogram_bins", sa.Integer(), primary_key=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("org_overview_snapshot")