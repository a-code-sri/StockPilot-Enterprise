"""
Outbox handlers for delivery projections.

Projection semantics (all days are UTC):
  - delivery_daily_status_counts: for orders CREATED on `day`, how many are
    currently in each status. Creation adds +1 'pending'; each change A->B moves
    one order from A to B on the order's creation day.
  - delivery_daily_item_counts: units ordered per product, counted ONCE per order
    on its creation day (previously re-added on every status change).
  - delivery_daily_counts / delivery_daily_hour_counts: deliveries completed per
    day and per hour of day, keyed by when the delivery happened.
"""

import logging
from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.core.time import parse_iso_datetime, utcnow
from backend.modules.delivery.infrastructure.projections import (
    DeliveryDailyCounts,
    DeliveryDailyHourCounts,
    DeliveryDailyItemCounts,
    DeliveryDailyStatusCounts,
)

logger = logging.getLogger(__name__)


def _upsert_counter(db: Session, model, keys: dict, column: str, delta: int) -> None:
    stmt = pg_insert(model).values(**keys, **{column: delta})
    stmt = stmt.on_conflict_do_update(
        index_elements=[getattr(model, k) for k in keys],
        set_={column: getattr(model, column) + getattr(stmt.excluded, column), "updated_at": func.now()},
    )
    db.execute(stmt)


def add_status(db: Session, day: date, status: str, delta: int) -> None:
    _upsert_counter(db, DeliveryDailyStatusCounts, {"day": day, "status": status}, "count", delta)


def add_item(db: Session, day: date, product_name: str, quantity: int) -> None:
    _upsert_counter(db, DeliveryDailyItemCounts, {"day": day, "product_name": product_name}, "quantity", quantity)


def add_delivered(db: Session, day: date, hour: int) -> None:
    _upsert_counter(db, DeliveryDailyCounts, {"day": day}, "delivered_count", 1)
    _upsert_counter(db, DeliveryDailyHourCounts, {"day": day, "hour": hour}, "count", 1)


def handle_delivery_changed(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    event_time = parse_iso_datetime(payload.get("timestamp")) or utcnow()
    created = parse_iso_datetime(payload.get("created_at")) or event_time
    created_day = created.date()

    from_status = str(payload.get("from_status") or "").strip().lower()
    to_status = str(payload.get("to_status") or "").strip().lower()

    logger.info("delivery: changed outbox_id=%s %s -> %s", outbox_id, from_status or "(new)", to_status)

    if from_status:
        add_status(db, created_day, from_status, -1)
    if to_status:
        add_status(db, created_day, to_status, +1)

    if not from_status:
        for item in payload.get("items") or []:
            name = str(item.get("product_name") or "").strip()
            try:
                qty = int(item.get("quantity") or 0)
            except (TypeError, ValueError):
                qty = 0
            if name and qty > 0:
                add_item(db, created_day, name, qty)

    if to_status == "delivered":
        add_delivered(db, event_time.date(), event_time.hour)


def handle_delivery_delivered(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    """Legacy event type from older versions; only counts the delivery."""
    when = parse_iso_datetime(payload.get("delivered_at") or payload.get("date")) or utcnow()
    add_delivered(db, when.date(), when.hour)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("delivery analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)
