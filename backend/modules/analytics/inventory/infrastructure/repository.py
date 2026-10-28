from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from backend.modules.inventory.infrastructure.models import InventoryItemModel, InventoryLogModel


class InventoryAnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_item_last_movement(self):
        # returns {item_id: last_timestamp}
        rows = (
            self.db.query(
                InventoryLogModel.item_id,
                func.max(InventoryLogModel.timestamp).label("last_ts")
            )
            .group_by(InventoryLogModel.item_id)
            .all()
        )
        return {r.item_id: r.last_ts for r in rows}

    def get_consumption_rates(self, days: int):
        since = datetime.utcnow() - timedelta(days=days)

        # consumption = consume + deliver
        rows = (
            self.db.query(
                InventoryLogModel.item_id,
                func.sum(InventoryLogModel.quantity).label("consumed_qty")
            )
            .filter(
                InventoryLogModel.timestamp >= since,
                InventoryLogModel.action.in_(["consume", "deliver"])
            )
            .group_by(InventoryLogModel.item_id)
            .all()
        )

        total_by_item = {r.item_id: float(r.consumed_qty or 0) for r in rows}
        rate_by_item = {item_id: (qty / max(days, 1)) for item_id, qty in total_by_item.items()}
        return rate_by_item, total_by_item

    def list_items(self):
        return self.db.query(InventoryItemModel).order_by(InventoryItemModel.name.asc()).all()

    def series_consumption_daily(self, days: int):
        since = datetime.utcnow() - timedelta(days=days)

        # PostgreSQL-friendly: date_trunc('day', timestamp)
        day_bucket = func.date_trunc("day", InventoryLogModel.timestamp)

        rows = (
            self.db.query(
                day_bucket.label("day"),
                func.sum(InventoryLogModel.quantity).label("qty")
            )
            .filter(
                InventoryLogModel.timestamp >= since,
                InventoryLogModel.action.in_(["consume", "deliver"])
            )
            .group_by(day_bucket)
            .order_by(day_bucket.asc())
            .all()
        )

        return [{"day": r.day.date().isoformat(), "quantity": float(r.qty or 0)} for r in rows]

    def series_orders_monthly(self, months: int):
        since = datetime.utcnow() - timedelta(days=months * 31)

        month_bucket = func.date_trunc("month", InventoryLogModel.timestamp)

        rows = (
            self.db.query(
                month_bucket.label("month"),
                func.sum(InventoryLogModel.quantity).label("qty")
            )
            .filter(
                InventoryLogModel.timestamp >= since,
                InventoryLogModel.action == "order"
            )
            .group_by(month_bucket)
            .order_by(month_bucket.asc())
            .all()
        )

        return [{"month": r.month.date().isoformat(), "quantity": float(r.qty or 0)} for r in rows]