from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.modules.delivery.infrastructure.models import DeliveryModel, DeliveryItemModel


ACTIVE_STATUSES = ["pending", "packed", "out_for_delivery"]
FINISHED_STATUSES = ["delivered", "failed", "cancelled"]


class DeliveryAnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def daily_delivered_counts(self, days: int):
        """
        Daily count of delivered orders using completed_at.
        Returns: [{day: 'YYYY-MM-DD', count: int}, ...]
        """
        since = datetime.utcnow() - timedelta(days=days)

        # group by date(completed_at)
        rows = (
            self.db.query(
                func.date(DeliveryModel.completed_at).label("day"),
                func.count(DeliveryModel.id).label("cnt"),
            )
            .filter(
                DeliveryModel.completed_at.isnot(None),
                DeliveryModel.status == "delivered",
                DeliveryModel.completed_at >= since,
            )
            .group_by(func.date(DeliveryModel.completed_at))
            .order_by(func.date(DeliveryModel.completed_at).asc())
            .all()
        )

        return [{"day": str(r.day), "count": int(r.cnt)} for r in rows]

    def status_distribution(self, days: int):
        """
        Count orders by current status for orders created within the window.
        Returns raw counts + consolidated 'active' bucket.
        """
        since = datetime.utcnow() - timedelta(days=days)

        rows = (
            self.db.query(
                DeliveryModel.status,
                func.count(DeliveryModel.id).label("cnt"),
            )
            .filter(DeliveryModel.created_at >= since)
            .group_by(DeliveryModel.status)
            .all()
        )

        raw = {str(r.status): int(r.cnt) for r in rows}
        active_total = sum(raw.get(s, 0) for s in ACTIVE_STATUSES)
        delivered = raw.get("delivered", 0)
        cancelled = raw.get("cancelled", 0)
        failed = raw.get("failed", 0)

        # anything else not in above buckets
        other = 0
        known = set(ACTIVE_STATUSES + ["delivered", "cancelled", "failed"])
        for k, v in raw.items():
            if k not in known:
                other += v

        consolidated = {
            "active": active_total,
            "delivered": delivered,
            "cancelled": cancelled,
            "failed": failed,
            "other": other,
        }

        return {
            "days": days,
            "raw": raw,
            "consolidated": consolidated
        }

    def most_ordered_items(self, days: int, top_n: int):
        """
        Top ordered products by total quantity over window.
        Uses deliveries.created_at filter.
        """
        since = datetime.utcnow() - timedelta(days=days)

        rows = (
            self.db.query(
                DeliveryItemModel.product_name,
                func.sum(DeliveryItemModel.quantity).label("qty"),
            )
            .join(DeliveryModel, DeliveryModel.id == DeliveryItemModel.delivery_id)
            .filter(DeliveryModel.created_at >= since)
            .group_by(DeliveryItemModel.product_name)
            .order_by(func.sum(DeliveryItemModel.quantity).desc())
            .limit(top_n)
            .all()
        )

        return [{"product_name": r.product_name, "quantity": float(r.qty or 0)} for r in rows]

    def delivered_completion_timestamps(self, days: int):
        """
        Returns list of datetime objects (completed_at) for delivered orders in window.
        We'll compute hour histogram in service (portable across DBs).
        """
        since = datetime.utcnow() - timedelta(days=days)

        rows = (
            self.db.query(DeliveryModel.completed_at)
            .filter(
                DeliveryModel.status == "delivered",
                DeliveryModel.completed_at.isnot(None),
                DeliveryModel.completed_at >= since,
            )
            .all()
        )
        return [r[0] for r in rows if r[0] is not None]