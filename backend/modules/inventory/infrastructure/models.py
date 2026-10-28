import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Float,
    Date,
    CheckConstraint,
    event,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import insert

from backend.core.database.base import Base
from backend.outbox.models import AnalyticsOutbox


class InventoryStatusEnum(str, enum.Enum):
    under_use = "under_use"
    ordered = "ordered"
    consumed = "consumed"


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    on_order_quantity = Column(Integer, nullable=False, default=0)

    price = Column(Float, nullable=False, default=0.0)

    status = Column(Enum(InventoryStatusEnum), nullable=False)
    expiry_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("InventoryLogModel", back_populates="item")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_non_negative"),
        CheckConstraint("on_order_quantity >= 0", name="ck_inventory_on_order_non_negative"),
        CheckConstraint("price >= 0", name="ck_inventory_price_non_negative"),
    )


class InventoryLogModel(Base):
    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"))
    action = Column(String)  # add / consume / deliver / order / status_change
    quantity = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    item = relationship("InventoryItemModel", back_populates="logs")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_inventory_log_quantity_positive"),
    )


@event.listens_for(InventoryLogModel, "after_insert")
def outbox_after_inventory_log_insert(mapper, connection, target: InventoryLogModel):
    action = (target.action or "").strip().lower()

    # Map actions -> analytics events
    if action in ("consume", "deliver"):
        event_type = "stock_consumed"
    elif action == "order":
        event_type = "purchase_order_created"
    else:
        return

    payload = {
        "log_id": target.id,
        "item_id": target.item_id,
        "quantity": target.quantity,
        "date": (target.timestamp or datetime.now(timezone.utc)).replace(tzinfo=timezone.utc).isoformat(),
        "action": action,
    }

    connection.execute(
        insert(AnalyticsOutbox).values(
            module="inventory",
            event_type=event_type,
            aggregate_type="inventory_log",
            aggregate_id=str(target.id),
            payload=payload,
            status="pending",
            available_at=datetime.now(timezone.utc),
        )
    )