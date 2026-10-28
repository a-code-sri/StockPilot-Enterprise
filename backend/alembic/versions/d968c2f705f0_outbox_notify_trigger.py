"""outbox_notify_trigger

Revision ID: d968c2f705f0
Revises: 99202356a1d1
Create Date: 2026-09-21 13:15:24.024221

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd968c2f705f0'
down_revision = '99202356a1d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION analytics_outbox_notify() RETURNS trigger AS $$
    BEGIN
      PERFORM pg_notify('analytics_outbox', NEW.id::text);
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS analytics_outbox_notify_trigger ON analytics_outbox;
    CREATE TRIGGER analytics_outbox_notify_trigger
    AFTER INSERT ON analytics_outbox
    FOR EACH ROW EXECUTE FUNCTION analytics_outbox_notify();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS analytics_outbox_notify_trigger ON analytics_outbox;")
    op.execute("DROP FUNCTION IF EXISTS analytics_outbox_notify();")