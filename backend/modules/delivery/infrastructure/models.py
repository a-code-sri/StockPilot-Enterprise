import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from backend.core.database.base import Base
from backend.core.time import ensure_utc, utcnow
from backend.outbox.repository import emit_event


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

    # True while linked inventory has been deducted for this delivery.
    stock_deducted = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

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
    # Optional link to stock; when set, dispatching the delivery deducts inventory.
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True, index=True)

    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False, default=0)

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

    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    delivery = relationship("DeliveryModel", back_populates="logs")


@event.listens_for(DeliveryLogModel, "after_insert")
def outbox_after_delivery_log_insert(mapper, connection, target: DeliveryLogModel):
    """Every status change (including creation, from_status=None) becomes one analytics event."""
    to_status = (target.to_status or "").strip().lower()
    if not to_status:
        return

    delivery = connection.execute(
        select(DeliveryModel.order_id, DeliveryModel.created_at).where(DeliveryModel.id == target.delivery_id)
    ).first()
    if not delivery:
        return

    items = []
    if target.from_status is None:
        # Item quantities only matter for the creation event (counted once per order).
        items = [
            {"product_name": r.product_name, "quantity": int(r.quantity), "unit_price": str(r.unit_price)}
            for r in connection.execute(
                select(DeliveryItemModel.product_name, DeliveryItemModel.quantity, DeliveryItemModel.unit_price).where(
                    DeliveryItemModel.delivery_id == target.delivery_id
                )
            )
        ]

    emit_event(
        connection,
        module="delivery",
        event_type="delivery_changed",
        aggregate_type="delivery",
        aggregate_id=str(target.delivery_id),
        payload={
            "delivery_log_id": target.id,
            "delivery_id": target.delivery_id,
            "order_id": delivery.order_id,
            "from_status": (target.from_status or None),
            "to_status": to_status,
            "timestamp": ensure_utc(target.timestamp or utcnow()).isoformat(),
            "created_at": ensure_utc(delivery.created_at).isoformat(),
            "items": items,
        },
    )
