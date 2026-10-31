"""overhaul v2: money as NUMERIC, UTC timestamps, stock-linked deliveries,
business profile, RBAC cascades, analytics repairs

Revision ID: f1c3a9d2b7e4
Revises: e4f7a2c91b30
Create Date: 2026-10-30

Data notes
- Naive timestamps were written with datetime.utcnow(), so they are converted
  with AT TIME ZONE 'UTC' (values are unchanged, only the type gains a zone).
- Float money columns are rounded to 2 decimals.
- Delivery projections were inflated (items re-counted on every status change),
  so they are rebuilt here from the source tables, and any not-yet-processed
  delivery events are superseded.
- Organization and project snapshots are rebuilt by queuing one event each.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f1c3a9d2b7e4"
down_revision = "e4f7a2c91b30"
branch_labels = None
depends_on = None

TIMESTAMP_COLUMNS = [
    ("transactions", "date"),
    ("inventory_items", "created_at"),
    ("inventory_logs", "timestamp"),
    ("deliveries", "created_at"),
    ("deliveries", "updated_at"),
    ("deliveries", "completed_at"),
    ("delivery_logs", "timestamp"),
    ("departments", "created_at"),
    ("employees", "created_at"),
    ("projects", "created_at"),
    ("project_tasks", "created_at"),
]
# Columns that become NOT NULL (nulls are back-filled with now()).
NOT_NULL_TIMESTAMPS = {
    ("transactions", "date"), ("inventory_items", "created_at"), ("inventory_logs", "timestamp"),
    ("departments", "created_at"), ("employees", "created_at"), ("projects", "created_at"),
    ("project_tasks", "created_at"),
}
MONEY_COLUMNS = [
    ("transactions", "amount"),
    ("inventory_items", "price"),
    ("delivery_items", "unit_price"),
    ("employees", "salary"),
]


def _replace_fk(table, column, ref_table, ref_column, ondelete):
    op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{table}_{column}_fkey"')
    op.create_foreign_key(f"{table}_{column}_fkey", table, ref_table, [column], [ref_column], ondelete=ondelete)


def upgrade() -> None:
    # ---------------- users / RBAC ----------------
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.alter_column("users", "is_active", nullable=False, server_default=sa.text("true"))
    _replace_fk("user_roles", "user_id", "users", "id", "CASCADE")
    _replace_fk("user_roles", "role_id", "roles", "id", "CASCADE")
    _replace_fk("role_permissions", "role_id", "roles", "id", "CASCADE")
    _replace_fk("role_permissions", "permission_id", "permissions", "id", "CASCADE")

    # ---------------- timestamps -> timestamptz (UTC) ----------------
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE TIMESTAMP WITH TIME ZONE '
            f"USING \"{column}\" AT TIME ZONE 'UTC'"
        )
        if (table, column) in NOT_NULL_TIMESTAMPS:
            op.execute(f'UPDATE {table} SET "{column}" = now() WHERE "{column}" IS NULL')
            op.alter_column(table, column, nullable=False)

    # ---------------- money -> NUMERIC(14,2) ----------------
    for table, column in MONEY_COLUMNS:
        op.alter_column(
            table, column, type_=sa.Numeric(14, 2), postgresql_using=f"round({column}::numeric, 2)"
        )
    # NOT VALID: enforce for new rows without failing on any legacy data.
    op.execute(
        "ALTER TABLE transactions ADD CONSTRAINT ck_transactions_amount_positive CHECK (amount > 0) NOT VALID"
    )

    # ---------------- inventory ----------------
    _replace_fk("inventory_logs", "item_id", "inventory_items", "id", "SET NULL")
    op.create_index("ix_inventory_logs_item_id", "inventory_logs", ["item_id"])
    op.create_index("ix_inventory_logs_action_timestamp", "inventory_logs", ["action", "timestamp"])
    op.add_column("inventory_logs", sa.Column("detail", sa.String(), nullable=True))
    op.execute("UPDATE inventory_logs SET action = 'unknown' WHERE action IS NULL")
    op.alter_column("inventory_logs", "action", nullable=False)
    # status_change rows used a dummy quantity of 1; they carry no quantity.
    op.drop_constraint("ck_inventory_log_quantity_positive", "inventory_logs", type_="check")
    op.execute("UPDATE inventory_logs SET quantity = NULL WHERE action = 'status_change'")
    op.create_check_constraint(
        "ck_inventory_log_quantity_positive", "inventory_logs", "quantity IS NULL OR quantity > 0"
    )
    # Never written by the application.
    op.drop_table("inventory_alerts_snapshot")

    # ---------------- delivery ----------------
    op.add_column(
        "deliveries", sa.Column("stock_deducted", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.add_column("delivery_items", sa.Column("inventory_item_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "delivery_items_inventory_item_id_fkey", "delivery_items", "inventory_items",
        ["inventory_item_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_delivery_items_inventory_item_id", "delivery_items", ["inventory_item_id"])

    # Rebuild delivery projections from source tables (UTC days).
    op.execute(
        "UPDATE analytics_outbox SET status = 'dead', "
        "last_error = coalesce(last_error, '') || '[superseded: projections rebuilt by migration f1c3a9d2b7e4]' "
        "WHERE module = 'delivery' AND status IN ('pending', 'failed', 'processing')"
    )
    for t in ("delivery_daily_counts", "delivery_daily_status_counts", "delivery_daily_item_counts",
              "delivery_daily_hour_counts"):
        op.execute(f"DELETE FROM {t}")
    op.execute("""
        INSERT INTO delivery_daily_status_counts (day, status, count)
        SELECT (created_at AT TIME ZONE 'UTC')::date, status::text, count(*)
        FROM deliveries GROUP BY 1, 2
    """)
    op.execute("""
        INSERT INTO delivery_daily_item_counts (day, product_name, quantity)
        SELECT (d.created_at AT TIME ZONE 'UTC')::date, i.product_name, sum(i.quantity)
        FROM delivery_items i JOIN deliveries d ON d.id = i.delivery_id GROUP BY 1, 2
    """)
    op.execute("""
        INSERT INTO delivery_daily_counts (day, delivered_count)
        SELECT (completed_at AT TIME ZONE 'UTC')::date, count(*)
        FROM deliveries WHERE status = 'delivered' AND completed_at IS NOT NULL GROUP BY 1
    """)
    op.execute("""
        INSERT INTO delivery_daily_hour_counts (day, hour, count)
        SELECT (completed_at AT TIME ZONE 'UTC')::date,
               extract(hour FROM completed_at AT TIME ZONE 'UTC')::int, count(*)
        FROM deliveries WHERE status = 'delivered' AND completed_at IS NOT NULL GROUP BY 1, 2
    """)

    # ---------------- organization / projects ----------------
    op.create_index("ix_employees_manager_id", "employees", ["manager_id"])
    op.execute(
        "UPDATE analytics_outbox SET status = 'dead', "
        "last_error = coalesce(last_error, '') || '[superseded: snapshot rebuild queued by migration f1c3a9d2b7e4]' "
        "WHERE module IN ('organization', 'projects') AND status IN ('pending', 'failed', 'processing')"
    )
    op.execute("DELETE FROM org_overview_snapshot")
    op.execute("""
        INSERT INTO analytics_outbox (module, event_type, aggregate_type, aggregate_id, payload, status)
        VALUES
          ('organization', 'org_changed', 'org', 'org', '{"reason": "migration_rebuild"}'::jsonb, 'pending'),
          ('projects', 'projects_changed', 'project', '0',
           '{"reason": "migration_rebuild", "project_id": null}'::jsonb, 'pending')
    """)

    # ---------------- business profile ----------------
    status_enum = postgresql.ENUM(
        "unverified", "format_verified", "verified", "rejected", name="business_verification_status"
    )
    status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "business_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("trade_name", sa.String(200), nullable=True),
        sa.Column("gstin", sa.String(15), nullable=True),
        sa.Column("pan", sa.String(10), nullable=True),
        sa.Column("cin", sa.String(21), nullable=True),
        sa.Column("state_code", sa.String(2), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column(
            "verification_status",
            postgresql.ENUM(name="business_verification_status", create_type=False),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("verification_report", postgresql.JSONB(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("id = 1", name="ck_business_profile_single_row"),
    )


def downgrade() -> None:
    op.drop_table("business_profile")
    postgresql.ENUM(name="business_verification_status").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_employees_manager_id", table_name="employees")

    op.drop_index("ix_delivery_items_inventory_item_id", table_name="delivery_items")
    op.drop_constraint("delivery_items_inventory_item_id_fkey", "delivery_items", type_="foreignkey")
    op.drop_column("delivery_items", "inventory_item_id")
    op.drop_column("deliveries", "stock_deducted")

    op.create_table(
        "inventory_alerts_snapshot",
        sa.Column("snapshot_date", sa.Date(), primary_key=True),
        sa.Column("dead_stock_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("near_expiry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reorder_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.drop_constraint("ck_inventory_log_quantity_positive", "inventory_logs", type_="check")
    op.execute("UPDATE inventory_logs SET quantity = 1 WHERE quantity IS NULL")
    op.create_check_constraint("ck_inventory_log_quantity_positive", "inventory_logs", "quantity > 0")
    op.alter_column("inventory_logs", "action", nullable=True)
    op.drop_column("inventory_logs", "detail")
    op.drop_index("ix_inventory_logs_action_timestamp", table_name="inventory_logs")
    op.drop_index("ix_inventory_logs_item_id", table_name="inventory_logs")
    op.execute('ALTER TABLE inventory_logs DROP CONSTRAINT IF EXISTS "inventory_logs_item_id_fkey"')
    op.create_foreign_key("inventory_logs_item_id_fkey", "inventory_logs", "inventory_items", ["item_id"], ["id"])

    op.drop_constraint("ck_transactions_amount_positive", "transactions", type_="check")
    for table, column in MONEY_COLUMNS:
        op.alter_column(table, column, type_=sa.Float(), postgresql_using=f"{column}::double precision")

    for table, column in TIMESTAMP_COLUMNS:
        if (table, column) in NOT_NULL_TIMESTAMPS and (table, column) not in {("inventory_logs", "timestamp")}:
            op.alter_column(table, column, nullable=True)
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE TIMESTAMP WITHOUT TIME ZONE '
            f"USING \"{column}\" AT TIME ZONE 'UTC'"
        )
    op.alter_column("inventory_logs", "timestamp", nullable=True)

    for table, column, ref in (
        ("user_roles", "user_id", "users"), ("user_roles", "role_id", "roles"),
        ("role_permissions", "role_id", "roles"), ("role_permissions", "permission_id", "permissions"),
    ):
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{table}_{column}_fkey"')
        op.create_foreign_key(f"{table}_{column}_fkey", table, ref, [column], ["id"])
    op.alter_column("users", "is_active", nullable=True, server_default=None)
