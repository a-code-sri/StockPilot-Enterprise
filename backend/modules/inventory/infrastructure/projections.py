from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    Index,
)
from sqlalchemy.sql import func

from backend.core.database.base import Base


class InventoryDailyConsumption(Base):
    """
    Aggregated consumption per day (all items combined).
    If later you want per-item analytics, introduce item_id as part of PK.
    """
    __tablename__ = "inventory_daily_consumption"

    day = Column(Date, primary_key=True)
    consumed_qty = Column(Numeric(14, 2), nullable=False, server_default="0")

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_inventory_daily_consumption_day", "day"),)


class InventoryMonthlyOrders(Base):
    """
    Aggregated order count per month.
    month is stored as first day of the month.
    """
    __tablename__ = "inventory_monthly_orders"

    month = Column(Date, primary_key=True)
    order_count = Column(Integer, nullable=False, server_default="0")

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_inventory_monthly_orders_month", "month"),)


class InventoryAlertsSnapshot(Base):
    """
    Snapshot counts for dashboard/alerts endpoint.
    snapshot_date is the day the snapshot was computed (first-class projection).
    """
    __tablename__ = "inventory_alerts_snapshot"

    snapshot_date = Column(Date, primary_key=True)

    dead_stock_count = Column(Integer, nullable=False, server_default="0")
    near_expiry_count = Column(Integer, nullable=False, server_default="0")
    reorder_count = Column(Integer, nullable=False, server_default="0")

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_inventory_alerts_snapshot_date", "snapshot_date"),)