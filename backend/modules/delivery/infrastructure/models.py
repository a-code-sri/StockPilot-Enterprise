import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, ForeignKey, Float,
    CheckConstraint, UniqueConstraint, Index, event
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import insert, select

from backend.core.database.base import Base
from backend.outbox.models import AnalyticsOutbox


class DeliveryStatusEnum(str, enum.Enum):
    pending = "pending"
    packed = "packed"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    cancelled = "cancelled"


class DeliveryModel(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True)
    order_id = Column(String, nullable=False, unique=True, index=True)
    customer_id = Column(String, nullable=False, index=True)

    status = Column(Enum(DeliveryStatusEnum), nullable=False, default=DeliveryStatusEnum.pending)

    remarks = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    items = relationship("DeliveryItemModel", back_populates="delivery", cascade="all, delete-orphan")
    logs = relationship("DeliveryLogModel", back_populates="delivery", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("order_id", name="uq_deliveries_order_id"),
        Index("ix_deliveries_status", "status"),
        Index("ix_deliveries_created_at", "created_at"),
        Index("ix_deliveries_completed_at", "completed_at"),
    )


class DeliveryItemModel(Base):
    __tablename__ = "delivery_items"

    id = Column(Integer, primary_key=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True)

    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False, default=0.0)

    delivery = relationship("DeliveryModel", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_delivery_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_delivery_item_unit_price_non_negative"),
        Index("ix_delivery_items_product_name", "product_name"),
    )


class DeliveryLogModel(Base):
    __tablename__ = "delivery_logs"

    id = Column(Integer, primary_key=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True)

    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    remark = Column(String, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    delivery = relationship("DeliveryModel", back_populates="logs")


@event.listens_for(DeliveryLogModel, "after_insert")
def outbox_after_delivery_log_insert(
    mapper,
    connection,
    target: DeliveryLogModel,
):
    to_status = (target.to_status or "").strip().lower()

    if not to_status:
        return

    delivery_row = connection.execute(
        select(
            DeliveryModel.order_id,
            DeliveryModel.customer_id,
            DeliveryModel.completed_at,
        ).where(
            DeliveryModel.id == target.delivery_id
        )
    ).first()

    if not delivery_row:
        return

    order_id = delivery_row.order_id
    customer_id = delivery_row.customer_id
    completed_at = delivery_row.completed_at

    delivery_items = connection.execute(
        select(
            DeliveryItemModel.product_name,
            DeliveryItemModel.quantity,
            DeliveryItemModel.unit_price,
        ).where(
            DeliveryItemModel.delivery_id == target.delivery_id
        )
    ).all()

    items = [
        {
            "product_name": item.product_name,
            "quantity": int(item.quantity),
            "unit_price": float(item.unit_price),
        }
        for item in delivery_items
    ]

    event_timestamp = target.timestamp or datetime.utcnow()

    payload = {
        "delivery_log_id": target.id,
        "delivery_id": target.delivery_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "from_status": target.from_status,
        "to_status": to_status,
        "timestamp": event_timestamp.replace(
            tzinfo=timezone.utc
        ).isoformat(),
        "completed_at": (
            completed_at.replace(
                tzinfo=timezone.utc
            ).isoformat()
            if completed_at
            else None
        ),
        "items": items,
    }

    connection.execute(
        insert(AnalyticsOutbox).values(
            module="delivery",
            event_type="delivery_changed",
            aggregate_type="delivery",
            aggregate_id=str(target.delivery_id),
            payload=payload,
            status="pending",
            available_at=datetime.now(timezone.utc),
        )
    )