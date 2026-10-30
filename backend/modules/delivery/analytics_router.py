from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.core.time import utctoday
from backend.modules.delivery.infrastructure.projections import (
    DeliveryDailyCounts,
    DeliveryDailyHourCounts,
    DeliveryDailyItemCounts,
    DeliveryDailyStatusCounts,
)

router = APIRouter()


def moving_average_series(counts_by_day: dict[date, int], start: date, end: date, window: int) -> list[dict]:
    """Trailing moving average over every day in [start, end] (missing days count as 0)."""
    series, counts = [], []
    for i in range((end - start).days + 1):
        day = start + timedelta(days=i)
        counts.append(int(counts_by_day.get(day, 0)))
        recent = counts[-window:]
        series.append({"day": day.isoformat(), "count": counts[-1], "moving_avg": sum(recent) / len(recent)})
    return series


def shift_hours(counts_by_utc_hour: dict[int, int], tz_offset_minutes: int) -> list[dict]:
    """Re-label UTC hour buckets as (approximate) local hours, rounding the offset to whole hours."""
    shift = round(tz_offset_minutes / 60)
    local: dict[int, int] = {h: 0 for h in range(24)}
    for utc_hour, count in counts_by_utc_hour.items():
        local[(utc_hour + shift) % 24] += count
    return [{"label": h, "value": local[h]} for h in range(24)]


def _sum_by(db: Session, key_col, value_col, day_col, start: date, end: date, order_by=None, limit=None):
    q = (
        db.query(key_col, func.sum(value_col))
        .filter(day_col >= start, day_col <= end)
        .group_by(key_col)
    )
    if order_by is not None:
        q = q.order_by(*order_by)
    if limit:
        q = q.limit(limit)
    return q.all()


def build_period(db: Session, days: int, window: int, top_n: int, tz_offset_minutes: int) -> dict:
    end = utctoday()
    start = end - timedelta(days=days - 1)

    delivered = dict(
        db.query(DeliveryDailyCounts.day, DeliveryDailyCounts.delivered_count)
        .filter(DeliveryDailyCounts.day >= start, DeliveryDailyCounts.day <= end)
        .all()
    )

    qty = func.sum(DeliveryDailyItemCounts.quantity)
    items = _sum_by(
        db, DeliveryDailyItemCounts.product_name, DeliveryDailyItemCounts.quantity, DeliveryDailyItemCounts.day,
        start, end, order_by=(qty.desc(), DeliveryDailyItemCounts.product_name.asc()), limit=top_n,
    )
    statuses = _sum_by(
        db, DeliveryDailyStatusCounts.status, DeliveryDailyStatusCounts.count, DeliveryDailyStatusCounts.day,
        start, end, order_by=(func.sum(DeliveryDailyStatusCounts.count).desc(),),
    )
    hours = _sum_by(
        db, DeliveryDailyHourCounts.hour, DeliveryDailyHourCounts.count, DeliveryDailyHourCounts.day, start, end
    )

    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "moving_average": {"window": window, "series": moving_average_series(delivered, start, end, window)},
        "most_ordered_items": {"top_n": top_n, "series": [{"label": n, "value": int(q or 0)} for n, q in items]},
        "status_distribution": {
            "series": [{"label": s, "value": int(c or 0)} for s, c in statuses if int(c or 0) > 0]
        },
        "peak_delivery_time_histogram": {
            "series": shift_hours({int(h): int(c or 0) for h, c in hours}, tz_offset_minutes),
            "tz_offset_minutes": tz_offset_minutes,
        },
    }


@router.get("/overview")
def delivery_overview(
    days_month: int = Query(30, ge=1, le=3650),
    days_year: int = Query(365, ge=1, le=3650),
    top_n: int = Query(10, ge=1, le=100),
    ma_window_month: int = Query(7, ge=1, le=365),
    ma_window_year: int = Query(30, ge=1, le=365),
    tz_offset_minutes: int = Query(0, ge=-720, le=840, description="Viewer's UTC offset, e.g. 330 for IST"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("delivery.read")),
):
    month = build_period(db, days_month, ma_window_month, top_n, tz_offset_minutes)
    year = build_period(db, days_year, ma_window_year, top_n, tz_offset_minutes)

    last_updated = max(
        (
            ts
            for ts in (
                db.query(func.max(m.updated_at)).scalar()
                for m in (DeliveryDailyCounts, DeliveryDailyStatusCounts, DeliveryDailyItemCounts, DeliveryDailyHourCounts)
            )
            if ts is not None
        ),
        default=None,
    )

    return {
        key: {"month": month[key], "year": year[key]}
        for key in ("moving_average", "most_ordered_items", "status_distribution", "peak_delivery_time_histogram")
    } | {"last_updated": last_updated.isoformat() if last_updated else None}
