"""
Read-side inventory analytics.

Time series come from projections. Alerts, reorder suggestions and stock-out
predictions are parameterised, so they are computed from the source tables
(one aggregate query each; fine for typical inventory sizes).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.analytics.stats import DEFAULT_Z_THRESHOLD, modified_z_scores
from backend.core.time import ensure_utc, utcnow, utctoday
from backend.modules.inventory.infrastructure.models import InventoryItemModel, InventoryLogModel
from backend.modules.inventory.infrastructure.projections import InventoryDailyConsumption, InventoryMonthlyOrders

CONSUMING_ACTIONS = ("consume", "deliver")


def _month_add(year: int, month: int, delta: int) -> tuple[int, int]:
    m = month + delta
    return year + (m - 1) // 12, (m - 1) % 12 + 1


def reorder_quantity(*, rate: float, coverage_days: int, quantity: int, on_order: int) -> float:
    """Units to order so stock + on-order covers `coverage_days` of consumption."""
    return max(0.0, rate * coverage_days - (quantity + on_order))


def days_to_stockout(*, rate: float, quantity: int) -> float | None:
    if rate <= 0:
        return None
    return quantity / rate if quantity > 0 else 0.0


class InventoryAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- shared queries ----------

    def _items(self):
        return self.db.query(InventoryItemModel).order_by(InventoryItemModel.name.asc()).all()

    def consumption_rates(self, days: int) -> tuple[dict[int, float], dict[int, float]]:
        """Returns ({item_id: units/day}, {item_id: units in window}), net of returns."""
        since = utcnow() - timedelta(days=days)
        rows = (
            self.db.query(InventoryLogModel.item_id, InventoryLogModel.action, func.sum(InventoryLogModel.quantity))
            .filter(
                InventoryLogModel.timestamp >= since,
                InventoryLogModel.item_id.isnot(None),
                InventoryLogModel.action.in_(CONSUMING_ACTIONS + ("return",)),
            )
            .group_by(InventoryLogModel.item_id, InventoryLogModel.action)
            .all()
        )
        totals: dict[int, float] = defaultdict(float)
        for item_id, action, qty in rows:
            totals[item_id] += float(qty or 0) * (-1 if action == "return" else 1)
        totals = {k: max(0.0, v) for k, v in totals.items()}
        rates = {k: v / max(days, 1) for k, v in totals.items()}
        return rates, totals

    def _last_consumption(self) -> dict[int, datetime]:
        rows = (
            self.db.query(InventoryLogModel.item_id, func.max(InventoryLogModel.timestamp))
            .filter(InventoryLogModel.action.in_(CONSUMING_ACTIONS))
            .group_by(InventoryLogModel.item_id)
            .all()
        )
        return {item_id: ts for item_id, ts in rows if item_id is not None}

    # ---------- endpoints ----------

    def series(self, consumption_days: int, order_months: int) -> dict:
        today = utctoday()
        start_day = today - timedelta(days=consumption_days - 1)
        consumption = dict(
            self.db.query(InventoryDailyConsumption.day, InventoryDailyConsumption.consumed_qty)
            .filter(InventoryDailyConsumption.day >= start_day, InventoryDailyConsumption.day <= today)
            .all()
        )
        daily = [
            {"label": (start_day + timedelta(days=i)).isoformat(),
             "value": float(consumption.get(start_day + timedelta(days=i), 0))}
            for i in range(consumption_days)
        ]

        this_month = date(today.year, today.month, 1)
        sy, sm = _month_add(this_month.year, this_month.month, -(order_months - 1))
        orders = dict(
            self.db.query(InventoryMonthlyOrders.month, InventoryMonthlyOrders.order_count)
            .filter(InventoryMonthlyOrders.month >= date(sy, sm, 1), InventoryMonthlyOrders.month <= this_month)
            .all()
        )
        monthly = []
        y, m = sy, sm
        for _ in range(order_months):
            md = date(y, m, 1)
            monthly.append({"label": md.isoformat()[:7], "value": float(orders.get(md, 0))})
            y, m = _month_add(y, m, 1)

        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        last_updated = self.db.query(
            func.greatest(
                func.coalesce(func.max(InventoryDailyConsumption.updated_at), epoch),
                func.coalesce(func.max(InventoryMonthlyOrders.updated_at), epoch),
            )
        ).scalar()

        return {
            "daily_consumption": {"days": consumption_days, "series": daily},
            "monthly_orders": {"months": order_months, "series": monthly},
            "last_updated": last_updated.isoformat() if last_updated and last_updated > epoch else None,
        }

    def alerts(self, dead_days: int, expiry_days: int, consumption_days: int, coverage_days: int = 14) -> dict:
        now = utcnow()
        today = now.date()
        items = self._items()
        rates, _ = self.consumption_rates(consumption_days)
        last_used = self._last_consumption()

        exhausted, dead_stock, near_expiry, reorder = [], [], [], []
        for it in items:
            rate = rates.get(it.id, 0.0)

            if it.quantity == 0:
                exhausted.append({"id": it.id, "name": it.name, "on_order_quantity": it.on_order_quantity})

            last = ensure_utc(last_used.get(it.id) or it.created_at)
            inactive = (now - last).days
            if it.quantity > 0 and inactive >= dead_days:
                dead_stock.append({"id": it.id, "name": it.name, "quantity": it.quantity, "days_inactive": inactive})

            if it.expiry_date and it.quantity > 0:
                to_expiry = (it.expiry_date - today).days
                to_consume = days_to_stockout(rate=rate, quantity=it.quantity)
                # Risky if it expires soon, or won't be used up before it expires.
                if to_expiry <= expiry_days or to_consume is None or to_consume > to_expiry:
                    near_expiry.append({
                        "id": it.id, "name": it.name, "quantity": it.quantity,
                        "expiry_date": it.expiry_date.isoformat(), "days_to_expiry": to_expiry,
                        "avg_daily_consumption": round(rate, 4),
                    })

            suggested = reorder_quantity(
                rate=rate, coverage_days=coverage_days, quantity=it.quantity, on_order=it.on_order_quantity
            )
            if suggested > 0 or (it.quantity == 0 and it.on_order_quantity == 0):
                reorder.append({"id": it.id, "name": it.name, "suggested_quantity": round(suggested, 2)})

        return {
            "params": {"dead_days": dead_days, "expiry_days": expiry_days, "consumption_days": consumption_days,
                       "coverage_days": coverage_days},
            "dead_stock_count": len(dead_stock),
            "near_expiry_count": len(near_expiry),
            "reorder_count": len(reorder),
            "exhausted_count": len(exhausted),
            "dead_stock": dead_stock,
            "near_expiry": near_expiry,
            "reorder": reorder,
            "exhausted": exhausted,
            "last_updated": now.isoformat(),
        }

    def reorder_suggestions(self, consumption_days: int, coverage_days: int) -> list[dict]:
        rates, totals = self.consumption_rates(consumption_days)
        out = []
        for it in self._items():
            rate = rates.get(it.id, 0.0)
            out.append({
                "id": it.id,
                "name": it.name,
                "current_quantity": it.quantity,
                "on_order_quantity": it.on_order_quantity,
                "avg_daily_consumption": round(rate, 4),
                "consumed_last_window": round(totals.get(it.id, 0.0), 2),
                "suggested_reorder_quantity": round(
                    reorder_quantity(rate=rate, coverage_days=coverage_days, quantity=it.quantity,
                                     on_order=it.on_order_quantity), 2),
            })
        out.sort(key=lambda x: x["suggested_reorder_quantity"], reverse=True)
        return out

    def stockout_predictions(self, consumption_days: int) -> list[dict]:
        rates, _ = self.consumption_rates(consumption_days)
        today = utctoday()
        out = []
        for it in self._items():
            rate = rates.get(it.id, 0.0)
            days = days_to_stockout(rate=rate, quantity=it.quantity)
            out.append({
                "id": it.id,
                "name": it.name,
                "current_quantity": it.quantity,
                "avg_daily_consumption": round(rate, 4),
                "days_to_stockout": None if days is None else round(days, 2),
                "predicted_stockout_date": None if days is None else (today + timedelta(days=int(days))).isoformat(),
            })
        out.sort(key=lambda x: (x["days_to_stockout"] is None, x["days_to_stockout"] or 0))
        return out

    def anomalies(self, days: int, limit: int) -> dict:
        """
        Days on which an item's consumption spiked versus its own history in the
        window (robust z-score over that item's daily totals, zero days included).
        """
        start = utctoday() - timedelta(days=days - 1)
        day_bucket = func.date_trunc("day", InventoryLogModel.timestamp)
        rows = (
            self.db.query(InventoryLogModel.item_id, day_bucket, func.sum(InventoryLogModel.quantity))
            .filter(
                InventoryLogModel.timestamp >= datetime(start.year, start.month, start.day, tzinfo=timezone.utc),
                InventoryLogModel.item_id.isnot(None),
                InventoryLogModel.action.in_(CONSUMING_ACTIONS),
            )
            .group_by(InventoryLogModel.item_id, day_bucket)
            .all()
        )
        per_item: dict[int, dict[date, float]] = defaultdict(dict)
        for item_id, bucket, qty in rows:
            per_item[item_id][ensure_utc(bucket).date()] = float(qty or 0)

        names = dict(self.db.query(InventoryItemModel.id, InventoryItemModel.name).all())
        found = []
        for item_id, by_day in per_item.items():
            if len(by_day) < 3:  # need a few active days for a meaningful baseline
                continue
            series = [by_day.get(start + timedelta(days=i), 0.0) for i in range(days)]
            active = [v for v in series if v > 0]
            typical = median(active)
            for i, z in enumerate(modified_z_scores(series)):
                qty = series[i]
                if z >= DEFAULT_Z_THRESHOLD and qty > typical:
                    found.append({
                        "item_id": item_id,
                        "name": names.get(item_id, f"#{item_id}"),
                        "day": (start + timedelta(days=i)).isoformat(),
                        "quantity": qty,
                        "typical_daily_quantity": round(typical, 2),
                        "score": round(z, 2),
                        "reason": f"Consumed {qty:g} units, {qty / typical:.1f}x the usual {typical:g} on active days",
                    })
        found.sort(key=lambda a: a["score"], reverse=True)
        return {"window_days": days, "items_scanned": len(per_item), "anomalies": found[:limit]}
