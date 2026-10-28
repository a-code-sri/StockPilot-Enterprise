"""create projects analytics projections

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
        "projects_portfolio_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "project_snapshot",
        sa.Column("project_id", sa.Integer(), primary_key=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("project_snapshot")
    op.drop_table("projects_portfolio_snapshot")