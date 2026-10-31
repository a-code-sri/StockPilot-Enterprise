from sqlalchemy import Column, Date, DateTime, Index, Integer, Numeric
from sqlalchemy.sql import func

from backend.core.database.base import Base


class InventoryDailyConsumption(Base):
    """Units consumed or delivered per UTC day (all items combined), net of returns."""

    __tablename__ = "inventory_daily_consumption"

    day = Column(Date, primary_key=True)
    consumed_qty = Column(Numeric(14, 2), nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_inventory_daily_consumption_day", "day"),)


class InventoryMonthlyOrders(Base):
    """Number of purchase orders per month; `month` is the first day of the month."""

    __tablename__ = "inventory_monthly_orders"

    month = Column(Date, primary_key=True)
    order_count = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_inventory_monthly_orders_month", "month"),)
