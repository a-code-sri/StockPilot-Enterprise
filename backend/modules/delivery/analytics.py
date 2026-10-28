import logging
from datetime import datetime, date, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.modules.delivery.infrastructure.projections import (
    DeliveryDailyCounts,
    DeliveryDailyStatusCounts,
    DeliveryDailyItemCounts,
    DeliveryDailyHourCounts,
)

logger = logging.getLogger(__name__)


def _parse_datetime(
    payload: dict[str, Any],
) -> datetime:
    raw = (
        payload.get("timestamp")
        or payload.get("delivered_at")
        or payload.get("date")
        or payload.get("day")
    )

    if isinstance(raw, datetime):
        return raw

    if isinstance(raw, date):
        return datetime(
            raw.year,
            raw.month,
            raw.day,
            tzinfo=timezone.utc,
        )

    if isinstance(raw, str):
        value = raw.strip()

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(value)

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed
        except Exception:
            pass

    return datetime.now(timezone.utc)


def _parse_day(
    payload: dict[str, Any],
) -> date:
    return _parse_datetime(payload).date()


def _upsert_delivered_count(
    db: Session,
    day: date,
) -> None:
    stmt = pg_insert(DeliveryDailyCounts).values(
        day=day,
        delivered_count=1,
    ).on_conflict_do_update(
        index_elements=[DeliveryDailyCounts.day],
        set_={
            "delivered_count": (
                DeliveryDailyCounts.delivered_count + 1
            ),
            "updated_at": func.now(),
        },
    )

    db.execute(stmt)


def _upsert_status_count(
    db: Session,
    day: date,
    status: str,
) -> None:
    stmt = pg_insert(
        DeliveryDailyStatusCounts
    ).values(
        day=day,
        status=status,
        count=1,
    ).on_conflict_do_update(
        index_elements=[
            DeliveryDailyStatusCounts.day,
            DeliveryDailyStatusCounts.status,
        ],
        set_={
            "count": (
                DeliveryDailyStatusCounts.count + 1
            ),
            "updated_at": func.now(),
        },
    )

    db.execute(stmt)


def _upsert_item_count(
    db: Session,
    day: date,
    product_name: str,
    quantity: int,
) -> None:
    stmt = pg_insert(
        DeliveryDailyItemCounts
    ).values(
        day=day,
        product_name=product_name,
        quantity=quantity,
    ).on_conflict_do_update(
        index_elements=[
            DeliveryDailyItemCounts.day,
            DeliveryDailyItemCounts.product_name,
        ],
        set_={
            "quantity": (
                DeliveryDailyItemCounts.quantity + quantity
            ),
            "updated_at": func.now(),
        },
    )

    db.execute(stmt)


def _upsert_delivery_hour(
    db: Session,
    day: date,
    hour: int,
) -> None:
    stmt = pg_insert(
        DeliveryDailyHourCounts
    ).values(
        day=day,
        hour=hour,
        count=1,
    ).on_conflict_do_update(
        index_elements=[
            DeliveryDailyHourCounts.day,
            DeliveryDailyHourCounts.hour,
        ],
        set_={
            "count": (
                DeliveryDailyHourCounts.count + 1
            ),
            "updated_at": func.now(),
        },
    )

    db.execute(stmt)


def handle_delivery_changed(
    db: Session,
    payload: dict[str, Any],
    outbox_id: int,
) -> None:
    event_time = _parse_datetime(payload)
    day = event_time.date()

    status = str(
        payload.get("to_status") or ""
    ).strip().lower()

    logger.info(
        "delivery analytics: delivery_changed "
        "outbox_id=%s day=%s status=%s",
        outbox_id,
        day,
        status,
    )

    if status:
        _upsert_status_count(
            db,
            day,
            status,
        )

    items = payload.get("items") or []

    for item in items:
        product_name = str(
            item.get("product_name") or ""
        ).strip()

        if not product_name:
            continue

        try:
            quantity = int(
                item.get("quantity") or 0
            )
        except Exception:
            quantity = 0

        if quantity <= 0:
            continue

        _upsert_item_count(
            db,
            day,
            product_name,
            quantity,
        )

    if status == "delivered":
        _upsert_delivered_count(
            db,
            day,
        )

        _upsert_delivery_hour(
            db,
            day,
            event_time.hour,
        )


def handle_delivery_delivered(
    db: Session,
    payload: dict[str, Any],
    outbox_id: int,
) -> None:
    """
    Compatibility handler for existing delivery_delivered
    outbox events created before the delivery_changed event
    was introduced.
    """

    day = _parse_day(payload)

    logger.info(
        "delivery analytics: delivery_delivered "
        "outbox_id=%s day=%s",
        outbox_id,
        day,
    )

    _upsert_delivered_count(
        db,
        day,
    )


def handle_event(
    db: Session,
    event_type: str,
    payload: dict[str, Any],
    outbox_id: int,
) -> None:
    logger.warning(
        "delivery analytics: unhandled event '%s' "
        "(outbox_id=%s)",
        event_type,
        outbox_id,
    )