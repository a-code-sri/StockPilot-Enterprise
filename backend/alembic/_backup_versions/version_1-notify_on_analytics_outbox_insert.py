"""notify on analytics_outbox insert

Revision ID: <PUT_REVISION_ID_HERE>
Revises: <PUT_DOWN_REVISION_ID_HERE>
Create Date: 2026-09-14
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "<PUT_REVISION_ID_HERE>"
down_revision = "<PUT_DOWN_REVISION_ID_HERE>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create trigger function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_analytics_outbox_insert()
        RETURNS trigger AS $$
        BEGIN
          -- Notify worker that a new outbox row exists.
          -- Payload is the inserted outbox id.
          PERFORM pg_notify('analytics_outbox', NEW.id::text);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_notify_analytics_outbox_insert ON analytics_outbox;
        CREATE TRIGGER trg_notify_analytics_outbox_insert
        AFTER INSERT ON analytics_outbox
        FOR EACH ROW
        EXECUTE FUNCTION notify_analytics_outbox_insert();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_notify_analytics_outbox_insert ON analytics_outbox;")
    op.execute("DROP FUNCTION IF EXISTS notify_analytics_outbox_insert();")