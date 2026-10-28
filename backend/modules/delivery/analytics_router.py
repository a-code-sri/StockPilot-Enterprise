from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission

from backend.modules.delivery.infrastructure.projections import (
    DeliveryDailyCounts,
    DeliveryDailyStatusCounts,
    DeliveryDailyItemCounts,
    DeliveryDailyHourCounts,
)


router = APIRouter()


def _build_moving_average_series(
    rows,
    start: date,
    end: date,
    window: int,
):
    values = {
        day: int(count or 0)
        for day, count in rows
    }

    total_days = (
        end - start
    ).days + 1

    series = []
    counts = []

    for i in range(total_days):
        day = start + timedelta(days=i)

        count = values.get(day, 0)

        counts.append(count)

        window_start = max(
            0,
            len(counts) - window,
        )

        window_values = counts[
            window_start:
        ]

        moving_avg = (
            sum(window_values)
            / max(1, len(window_values))
        )

        series.append(
            {
                "day": day.isoformat(),
                "count": count,
                "moving_avg": moving_avg,
            }
        )

    return series


def _date_range(days: int):
    today = date.today()

    start = today - timedelta(
        days=days - 1
    )

    return start, today


def _top_items(
    db: Session,
    start: date,
    end: date,
    top_n: int,
):
    rows = (
        db.query(
            DeliveryDailyItemCounts.product_name,
            func.sum(
                DeliveryDailyItemCounts.quantity
            ).label("quantity"),
        )
        .filter(
            DeliveryDailyItemCounts.day >= start,
            DeliveryDailyItemCounts.day <= end,
        )
        .group_by(
            DeliveryDailyItemCounts.product_name
        )
        .order_by(
            func.sum(
                DeliveryDailyItemCounts.quantity
            ).desc(),
            DeliveryDailyItemCounts.product_name.asc(),
        )
        .limit(top_n)
        .all()
    )

    return [
        {
            "label": product_name,
            "value": int(quantity or 0),
        }
        for product_name, quantity in rows
    ]


def _status_distribution(
    db: Session,
    start: date,
    end: date,
):
    rows = (
        db.query(
            DeliveryDailyStatusCounts.status,
            func.sum(
                DeliveryDailyStatusCounts.count
            ).label("count"),
        )
        .filter(
            DeliveryDailyStatusCounts.day >= start,
            DeliveryDailyStatusCounts.day <= end,
        )
        .group_by(
            DeliveryDailyStatusCounts.status
        )
        .order_by(
            func.sum(
                DeliveryDailyStatusCounts.count
            ).desc(),
            DeliveryDailyStatusCounts.status.asc(),
        )
        .all()
    )

    return [
        {
            "label": status,
            "value": int(count or 0),
        }
        for status, count in rows
    ]


def _peak_delivery_hours(
    db: Session,
    start: date,
    end: date,
):
    rows = (
        db.query(
            DeliveryDailyHourCounts.hour,
            func.sum(
                DeliveryDailyHourCounts.count
            ).label("count"),
        )
        .filter(
            DeliveryDailyHourCounts.day >= start,
            DeliveryDailyHourCounts.day <= end,
        )
        .group_by(
            DeliveryDailyHourCounts.hour
        )
        .order_by(
            DeliveryDailyHourCounts.hour.asc()
        )
        .all()
    )

    counts = {
        int(hour): int(count or 0)
        for hour, count in rows
    }

    return [
        {
            "label": hour,
            "value": counts.get(hour, 0),
        }
        for hour in range(24)
    ]


def _build_period(
    db: Session,
    days: int,
    moving_average_window: int,
    top_n: int,
):
    start, end = _date_range(days)

    delivery_rows = (
        db.query(
            DeliveryDailyCounts.day,
            DeliveryDailyCounts.delivered_count,
        )
        .filter(
            DeliveryDailyCounts.day >= start,
            DeliveryDailyCounts.day <= end,
        )
        .order_by(
            DeliveryDailyCounts.day.asc()
        )
        .all()
    )

    return {
        "range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "moving_average": {
            "window": moving_average_window,
            "series": _build_moving_average_series(
                delivery_rows,
                start,
                end,
                moving_average_window,
            ),
        },
        "most_ordered_items": {
            "top_n": top_n,
            "series": _top_items(
                db,
                start,
                end,
                top_n,
            ),
        },
        "status_distribution": {
            "series": _status_distribution(
                db,
                start,
                end,
            ),
        },
        "peak_delivery_time_histogram": {
            "series": _peak_delivery_hours(
                db,
                start,
                end,
            ),
        },
    }


@router.get("/overview")
def delivery_overview(
    days_month: int = Query(
        30,
        ge=1,
        le=3650,
    ),
    days_year: int = Query(
        365,
        ge=1,
        le=3650,
    ),
    top_n: int = Query(
        10,
        ge=1,
        le=100,
    ),
    ma_window_month: int = Query(
        7,
        ge=1,
        le=365,
    ),
    ma_window_year: int = Query(
        30,
        ge=1,
        le=365,
    ),
    db: Session = Depends(
        DatabaseAdapter.get_db
    ),
    user=Depends(
        require_permission("delivery.read")
    ),
):
    month = _build_period(
        db=db,
        days=days_month,
        moving_average_window=ma_window_month,
        top_n=top_n,
    )

    year = _build_period(
        db=db,
        days=days_year,
        moving_average_window=ma_window_year,
        top_n=top_n,
    )

    latest_delivery_update = db.query(
        func.max(
            DeliveryDailyCounts.updated_at
        )
    ).scalar()

    latest_status_update = db.query(
        func.max(
            DeliveryDailyStatusCounts.updated_at
        )
    ).scalar()

    latest_item_update = db.query(
        func.max(
            DeliveryDailyItemCounts.updated_at
        )
    ).scalar()

    latest_hour_update = db.query(
        func.max(
            DeliveryDailyHourCounts.updated_at
        )
    ).scalar()

    timestamps = [
        value
        for value in (
            latest_delivery_update,
            latest_status_update,
            latest_item_update,
            latest_hour_update,
        )
        if value is not None
    ]

    last_updated = (
        max(timestamps)
        if timestamps
        else None
    )

    return {
        "moving_average": {
            "month": month["moving_average"],
            "year": year["moving_average"],
        },
        "most_ordered_items": {
            "month": month["most_ordered_items"],
            "year": year["most_ordered_items"],
        },
        "status_distribution": {
            "month": month["status_distribution"],
            "year": year["status_distribution"],
        },
        "peak_delivery_time_histogram": {
            "month": month[
                "peak_delivery_time_histogram"
            ],
            "year": year[
                "peak_delivery_time_histogram"
            ],
        },
        "last_updated": (
            last_updated.isoformat()
            if last_updated
            else None
        ),
    }