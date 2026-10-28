from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.inventory.infrastructure.projections import (
    InventoryDailyConsumption,
    InventoryMonthlyOrders,
)
from backend.modules.inventory.infrastructure.models import InventoryItemModel, InventoryLogModel

router = APIRouter()


def _month_add(year: int, month: int, delta: int) -> tuple[int, int]:
    m = month + delta
    y = year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return y, m


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


@router.get("/series")
def inventory_series(
    consumption_days: int = Query(14, ge=1, le=3650),
    order_months: int = Query(6, ge=1, le=120),
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.read")),
):
    today = date.today()

    # Daily consumption series
    start_day = today - timedelta(days=consumption_days - 1)
    consumption_rows = (
        db.query(InventoryDailyConsumption.day, InventoryDailyConsumption.consumed_qty)
        .filter(InventoryDailyConsumption.day >= start_day, InventoryDailyConsumption.day <= today)
        .order_by(InventoryDailyConsumption.day.asc())
        .all()
    )
    consumption_map = {d: float(q or 0) for (d, q) in consumption_rows}

    daily_series = []
    for i in range(consumption_days):
        d = start_day + timedelta(days=i)
        daily_series.append({"label": d.isoformat(), "value": consumption_map.get(d, 0.0)})

    # Monthly orders series
    this_month = _month_start(today)
    start_year, start_month = _month_add(this_month.year, this_month.month, -(order_months - 1))
    start_month_date = date(start_year, start_month, 1)

    order_rows = (
        db.query(InventoryMonthlyOrders.month, InventoryMonthlyOrders.order_count)
        .filter(InventoryMonthlyOrders.month >= start_month_date, InventoryMonthlyOrders.month <= this_month)
        .order_by(InventoryMonthlyOrders.month.asc())
        .all()
    )
    orders_map = {m: int(c or 0) for (m, c) in order_rows}

    monthly_series = []
    y, m = start_year, start_month
    for _ in range(order_months):
        md = date(y, m, 1)
        monthly_series.append({"label": md.isoformat()[:7], "value": float(orders_map.get(md, 0))})
        y, m = _month_add(y, m, 1)

    last_updated = db.query(
        func.greatest(
            func.coalesce(func.max(InventoryDailyConsumption.updated_at), datetime(1970, 1, 1, tzinfo=timezone.utc)),
            func.coalesce(func.max(InventoryMonthlyOrders.updated_at), datetime(1970, 1, 1, tzinfo=timezone.utc)),
        )
    ).scalar()

    return {
        "daily_consumption": {"days": consumption_days, "series": daily_series},
        "monthly_orders": {"months": order_months, "series": monthly_series},
        "last_updated": last_updated.isoformat() if last_updated else None,
    }


@router.get("/alerts")
def inventory_alerts(
    dead_days: int = Query(30, ge=1, le=3650),
    expiry_days: int = Query(14, ge=1, le=3650),
    consumption_days: int = Query(14, ge=1, le=3650),
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.read")),
):
    """
    Alerts are parameterized (dead_days/expiry_days/consumption_days), so we compute them
    from source tables (fast enough for typical inventory sizes), rather than trying to
    precompute a snapshot for every parameter combination.
    """
    now = datetime.now(timezone.utc)
    dead_threshold = now - timedelta(days=dead_days)
    expiry_threshold = date.today() + timedelta(days=expiry_days)

    # last consumption per item_id
    last_consume_subq = (
        db.query(
            InventoryLogModel.item_id.label("item_id"),
            func.max(InventoryLogModel.timestamp).label("last_consume_at"),
        )
        .filter(InventoryLogModel.action == "consume")
        .group_by(InventoryLogModel.item_id)
        .subquery()
    )

    # Dead stock: qty > 0 and (last consume older than threshold OR never consumed and created_at older than threshold)
    dead_stock_count = (
        db.query(func.count(InventoryItemModel.id))
        .outerjoin(last_consume_subq, last_consume_subq.c.item_id == InventoryItemModel.id)
        .filter(
            InventoryItemModel.quantity > 0,
            func.coalesce(last_consume_subq.c.last_consume_at, InventoryItemModel.created_at) < dead_threshold.replace(tzinfo=None),
        )
        .scalar()
        or 0
    )

    # Near expiry: expiry_date set and within expiry_days
    near_expiry_count = (
        db.query(func.count(InventoryItemModel.id))
        .filter(
            InventoryItemModel.expiry_date.isnot(None),
            InventoryItemModel.expiry_date <= expiry_threshold,
            InventoryItemModel.quantity > 0,
        )
        .scalar()
        or 0
    )

    # Reorder: simplistic rule based on available fields
    reorder_count = (
        db.query(func.count(InventoryItemModel.id))
        .filter(
            InventoryItemModel.quantity == 0,
            InventoryItemModel.on_order_quantity == 0,
        )
        .scalar()
        or 0
    )

    return {
        "params": {"dead_days": dead_days, "expiry_days": expiry_days, "consumption_days": consumption_days},
        "dead_stock_count": int(dead_stock_count),
        "near_expiry_count": int(near_expiry_count),
        "reorder_count": int(reorder_count),
        "last_updated": now.isoformat(),
    }