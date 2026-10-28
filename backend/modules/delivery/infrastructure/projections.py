from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.sql import func

from backend.core.database.base import Base


class DeliveryDailyCounts(Base):
    __tablename__ = "delivery_daily_counts"

    day = Column(Date, primary_key=True)

    delivered_count = Column(
        Integer,
        nullable=False,
        server_default="0",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_delivery_daily_counts_day",
            "day",
        ),
    )


class DeliveryDailyStatusCounts(Base):
    __tablename__ = "delivery_daily_status_counts"

    day = Column(
        Date,
        primary_key=True,
        nullable=False,
    )

    status = Column(
        String,
        primary_key=True,
        nullable=False,
    )

    count = Column(
        Integer,
        nullable=False,
        server_default="0",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_delivery_daily_status_day",
            "day",
        ),
        Index(
            "ix_delivery_daily_status_status",
            "status",
        ),
    )


class DeliveryDailyItemCounts(Base):
    __tablename__ = "delivery_daily_item_counts"

    day = Column(
        Date,
        primary_key=True,
        nullable=False,
    )

    product_name = Column(
        String,
        primary_key=True,
        nullable=False,
    )

    quantity = Column(
        Integer,
        nullable=False,
        server_default="0",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_delivery_daily_item_day",
            "day",
        ),
        Index(
            "ix_delivery_daily_item_product",
            "product_name",
        ),
    )


class DeliveryDailyHourCounts(Base):
    __tablename__ = "delivery_daily_hour_counts"

    day = Column(
        Date,
        primary_key=True,
        nullable=False,
    )

    hour = Column(
        Integer,
        primary_key=True,
        nullable=False,
    )

    count = Column(
        Integer,
        nullable=False,
        server_default="0",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_delivery_daily_hour_day",
            "day",
        ),
        Index(
            "ix_delivery_daily_hour_hour",
            "hour",
        ),
    )