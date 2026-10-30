from sqlalchemy import Column, Date, DateTime, Index, Integer, String
from sqlalchemy.sql import func

from backend.core.database.base import Base


def _updated_at():
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class DeliveryDailyCounts(Base):
    """Deliveries completed per UTC day."""

    __tablename__ = "delivery_daily_counts"

    day = Column(Date, primary_key=True)
    delivered_count = Column(Integer, nullable=False, server_default="0")
    updated_at = _updated_at()

    __table_args__ = (Index("ix_delivery_daily_counts_day", "day"),)


class DeliveryDailyStatusCounts(Base):
    """For orders created on `day`, how many are currently in `status`."""

    __tablename__ = "delivery_daily_status_counts"

    day = Column(Date, primary_key=True, nullable=False)
    status = Column(String, primary_key=True, nullable=False)
    count = Column(Integer, nullable=False, server_default="0")
    updated_at = _updated_at()

    __table_args__ = (
        Index("ix_delivery_daily_status_day", "day"),
        Index("ix_delivery_daily_status_status", "status"),
    )


class DeliveryDailyItemCounts(Base):
    """Units ordered per product, for orders created on `day`."""

    __tablename__ = "delivery_daily_item_counts"

    day = Column(Date, primary_key=True, nullable=False)
    product_name = Column(String, primary_key=True, nullable=False)
    quantity = Column(Integer, nullable=False, server_default="0")
    updated_at = _updated_at()

    __table_args__ = (
        Index("ix_delivery_daily_item_day", "day"),
        Index("ix_delivery_daily_item_product", "product_name"),
    )


class DeliveryDailyHourCounts(Base):
    """Deliveries completed per UTC day and UTC hour (0-23)."""

    __tablename__ = "delivery_daily_hour_counts"

    day = Column(Date, primary_key=True, nullable=False)
    hour = Column(Integer, primary_key=True, nullable=False)
    count = Column(Integer, nullable=False, server_default="0")
    updated_at = _updated_at()

    __table_args__ = (
        Index("ix_delivery_daily_hour_day", "day"),
        Index("ix_delivery_daily_hour_hour", "hour"),
    )
