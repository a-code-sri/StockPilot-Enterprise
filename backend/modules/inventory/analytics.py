import logging
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.modules.inventory.infrastructure.projections import (
    InventoryDailyConsumption,
    InventoryMonthlyOrders,
    InventoryAlertsSnapshot,
)

logger = logging.getLogger(__name__)


def _as_decimal(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _parse_day(payload: dict[str, Any]) -> date:
    raw = payload.get("date") or payload.get("day")
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        s = raw.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return datetime.now(timezone.utc).date()
    return datetime.now(timezone.utc).date()


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def handle_stock_consumed(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    """
    Expected payload (minimum):
      - date: ISO string
      - quantity: number (consumed quantity, positive)
    """
    day = _parse_day(payload)
    qty = _as_decimal(payload.get("quantity"))

    logger.info("inventory analytics: stock_consumed outbox_id=%s qty=%s day=%s", outbox_id, qty, day)

    stmt = pg_insert(InventoryDailyConsumption).values(
        day=day,
        consumed_qty=qty,
    ).on_conflict_do_update(
        index_elements=[InventoryDailyConsumption.day],
        set_={
            "consumed_qty": InventoryDailyConsumption.consumed_qty + func.cast(qty, InventoryDailyConsumption.consumed_qty.type),
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)


def handle_purchase_order_created(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    """
    Expected payload (minimum):
      - date: ISO string (order created date)
    """
    day = _parse_day(payload)
    m = _month_start(day)

    logger.info("inventory analytics: purchase_order_created outbox_id=%s month=%s", outbox_id, m)

    stmt = pg_insert(InventoryMonthlyOrders).values(
        month=m,
        order_count=1,
    ).on_conflict_do_update(
        index_elements=[InventoryMonthlyOrders.month],
        set_={
            "order_count": InventoryMonthlyOrders.order_count + 1,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)


def handle_alerts_snapshot_updated(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    """
    This handler is for writing snapshot counts computed elsewhere (later).
    Expected payload:
      - snapshot_date: ISO date or datetime
      - dead_stock_count, near_expiry_count, reorder_count
    """
    raw = payload.get("snapshot_date") or payload.get("date") or payload.get("day")
    if isinstance(raw, datetime):
        snap = raw.date()
    elif isinstance(raw, str):
        try:
            snap = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except Exception:
            snap = datetime.now(timezone.utc).date()
    else:
        snap = datetime.now(timezone.utc).date()

    dead = int(payload.get("dead_stock_count") or 0)
    near = int(payload.get("near_expiry_count") or 0)
    reorder = int(payload.get("reorder_count") or 0)

    logger.info("inventory analytics: alerts_snapshot_updated outbox_id=%s snap=%s", outbox_id, snap)

    stmt = pg_insert(InventoryAlertsSnapshot).values(
        snapshot_date=snap,
        dead_stock_count=dead,
        near_expiry_count=near,
        reorder_count=reorder,
    ).on_conflict_do_update(
        index_elements=[InventoryAlertsSnapshot.snapshot_date],
        set_={
            "dead_stock_count": dead,
            "near_expiry_count": near,
            "reorder_count": reorder,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    """
    Fallback: keep pipeline healthy while you gradually wire inventory write events.
    """
    logger.warning("inventory analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)