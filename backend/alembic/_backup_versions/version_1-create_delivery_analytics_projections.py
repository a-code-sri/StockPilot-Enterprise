from sqlalchemy import Column, Date, DateTime, Integer, Index
from sqlalchemy.sql import func

from backend.core.database.base import Base


class DeliveryDailyCounts(Base):
    __tablename__ = "delivery_daily_counts"

    day = Column(Date, primary_key=True)
    delivered_count = Column(Integer, nullable=False, server_default="0")

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_delivery_daily_counts_day", "day"),)