"""Outbox handlers that maintain the inventory projections (UTC-day buckets)."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.core.time import parse_iso_datetime, utctoday
from backend.modules.inventory.infrastructure.projections import InventoryDailyConsumption, InventoryMonthlyOrders

logger = logging.getLogger(__name__)


def _as_decimal(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _parse_day(payload: dict[str, Any]) -> date:
    dt = parse_iso_datetime(payload.get("date") or payload.get("day"))
    return dt.date() if dt else utctoday()


def add_consumption(db: Session, day: date, qty: Decimal) -> None:
    stmt = pg_insert(InventoryDailyConsumption).values(day=day, consumed_qty=qty)
    stmt = stmt.on_conflict_do_update(
        index_elements=[InventoryDailyConsumption.day],
        set_={
            "consumed_qty": InventoryDailyConsumption.consumed_qty + stmt.excluded.consumed_qty,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)


def add_order(db: Session, month: date, count: int = 1) -> None:
    stmt = pg_insert(InventoryMonthlyOrders).values(month=month, order_count=count)
    stmt = stmt.on_conflict_do_update(
        index_elements=[InventoryMonthlyOrders.month],
        set_={"order_count": InventoryMonthlyOrders.order_count + stmt.excluded.order_count, "updated_at": func.now()},
    )
    db.execute(stmt)


def handle_stock_consumed(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    day, qty = _parse_day(payload), _as_decimal(payload.get("quantity"))
    logger.info("inventory: stock_consumed outbox_id=%s qty=%s day=%s", outbox_id, qty, day)
    add_consumption(db, day, qty)


def handle_stock_returned(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    """Returned stock (e.g. cancelled delivery) is netted out of that day's consumption."""
    day, qty = _parse_day(payload), _as_decimal(payload.get("quantity"))
    logger.info("inventory: stock_returned outbox_id=%s qty=%s day=%s", outbox_id, qty, day)
    add_consumption(db, day, -qty)


def handle_purchase_order_created(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    day = _parse_day(payload)
    month = date(day.year, day.month, 1)
    logger.info("inventory: purchase_order_created outbox_id=%s month=%s", outbox_id, month)
    add_order(db, month)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("inventory analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)
