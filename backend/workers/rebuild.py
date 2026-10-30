"""
Rebuild analytics projections from the source tables.

    python -m backend.workers.rebuild                 # all modules
    python -m backend.workers.rebuild delivery accounts

Use after fixing a projection bug or restoring a backup. Stop the analytics
worker first: events that are still queued for a rebuilt module are marked
superseded (the rebuild already reflects them), and running both at once could
count an event twice. Everything happens in one transaction.
"""

from __future__ import annotations

import argparse
import json
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.database.registry import import_all_models
from backend.core.database.session import SessionLocal

logger = logging.getLogger("rebuild")

SQL: dict[str, list[str]] = {
    "accounts": [
        "DELETE FROM accounts_daily_totals",
        "DELETE FROM accounts_daily_category_totals",
        """INSERT INTO accounts_daily_totals (day, income, expenses)
           SELECT (date AT TIME ZONE 'UTC')::date,
                  coalesce(sum(amount) FILTER (WHERE transaction_type = 'credit'), 0),
                  coalesce(sum(amount) FILTER (WHERE transaction_type = 'debit'), 0)
           FROM transactions GROUP BY 1""",
        """INSERT INTO accounts_daily_category_totals (day, category, transaction_type, amount)
           SELECT (date AT TIME ZONE 'UTC')::date, coalesce(category, 'Uncategorized'),
                  transaction_type::text, sum(amount)
           FROM transactions GROUP BY 1, 2, 3""",
    ],
    "inventory": [
        "DELETE FROM inventory_daily_consumption",
        "DELETE FROM inventory_monthly_orders",
        """INSERT INTO inventory_daily_consumption (day, consumed_qty)
           SELECT (timestamp AT TIME ZONE 'UTC')::date,
                  sum(CASE WHEN action = 'return' THEN -quantity ELSE quantity END)
           FROM inventory_logs WHERE action IN ('consume', 'deliver', 'return') GROUP BY 1""",
        """INSERT INTO inventory_monthly_orders (month, order_count)
           SELECT date_trunc('month', timestamp AT TIME ZONE 'UTC')::date, count(*)
           FROM inventory_logs WHERE action = 'order' GROUP BY 1""",
    ],
    "delivery": [
        "DELETE FROM delivery_daily_counts",
        "DELETE FROM delivery_daily_status_counts",
        "DELETE FROM delivery_daily_item_counts",
        "DELETE FROM delivery_daily_hour_counts",
        """INSERT INTO delivery_daily_status_counts (day, status, count)
           SELECT (created_at AT TIME ZONE 'UTC')::date, status::text, count(*) FROM deliveries GROUP BY 1, 2""",
        """INSERT INTO delivery_daily_item_counts (day, product_name, quantity)
           SELECT (d.created_at AT TIME ZONE 'UTC')::date, i.product_name, sum(i.quantity)
           FROM delivery_items i JOIN deliveries d ON d.id = i.delivery_id GROUP BY 1, 2""",
        """INSERT INTO delivery_daily_counts (day, delivered_count)
           SELECT (completed_at AT TIME ZONE 'UTC')::date, count(*)
           FROM deliveries WHERE status = 'delivered' AND completed_at IS NOT NULL GROUP BY 1""",
        """INSERT INTO delivery_daily_hour_counts (day, hour, count)
           SELECT (completed_at AT TIME ZONE 'UTC')::date, extract(hour FROM completed_at AT TIME ZONE 'UTC')::int,
                  count(*)
           FROM deliveries WHERE status = 'delivered' AND completed_at IS NOT NULL GROUP BY 1, 2""",
    ],
}

MODULES = ("accounts", "inventory", "delivery", "organization", "projects")


def _supersede_queued(db: Session, module: str) -> int:
    result = db.execute(
        text(
            "UPDATE analytics_outbox SET status = 'dead', "
            "last_error = coalesce(last_error, '') || '[superseded by projection rebuild]' "
            "WHERE module = :m AND status IN ('pending', 'failed')"
        ),
        {"m": module},
    )
    return result.rowcount or 0


def rebuild(db: Session, modules: list[str]) -> None:
    for module in modules:
        skipped = _supersede_queued(db, module)
        if module in SQL:
            for stmt in SQL[module]:
                db.execute(text(stmt))
        elif module == "organization":
            from backend.modules.organization.analytics import handle_org_changed

            db.execute(text("DELETE FROM org_overview_snapshot"))
            handle_org_changed(db, {"reason": "rebuild"}, outbox_id=0)
        elif module == "projects":
            from backend.modules.projects.analytics import handle_projects_changed

            handle_projects_changed(db, {"reason": "rebuild", "project_id": None}, outbox_id=0)
        logger.info("Rebuilt %s projections (%s queued events superseded)", module, skipped)

    # Tell open dashboards to refresh.
    for module in modules:
        db.execute(
            text("SELECT pg_notify(:channel, :payload)"),
            {
                "channel": get_settings().REALTIME_LISTEN_CHANNEL,
                "payload": json.dumps({"type": "analytics.updated", "module": module, "event_type": "rebuild"}),
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("modules", nargs="*", help=f"any of: {', '.join(MODULES)} (default: all)")
    args = parser.parse_args()
    unknown = sorted(set(args.modules) - set(MODULES))
    if unknown:
        parser.error(f"unknown module(s): {', '.join(unknown)}")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")

    import_all_models()
    modules = args.modules or list(MODULES)
    db = SessionLocal()
    try:
        rebuild(db, modules)
        db.commit()
        print(f"Rebuilt: {', '.join(modules)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
