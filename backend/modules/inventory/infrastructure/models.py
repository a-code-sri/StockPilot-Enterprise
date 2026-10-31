import enum

from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, event
from sqlalchemy.orm import relationship

from backend.core.database.base import Base
from backend.core.time import ensure_utc, utcnow
from backend.outbox.repository import emit_event


class InventoryStatusEnum(str, enum.Enum):
    under_use = "under_use"
    ordered = "ordered"
    consumed = "consumed"


class InventoryAction(str, enum.Enum):
    add = "add"              # stock received (also reduces on-order quantity)
    consume = "consume"      # used internally
    deliver = "deliver"      # shipped to a customer (delivery module)
    order = "order"          # purchase order placed (increases on-order quantity)
    return_ = "return"       # stock came back (e.g. cancelled delivery)
    status_change = "status_change"


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    on_order_quantity = Column(Integer, nullable=False, default=0)

    price = Column(Numeric(14, 2), nullable=False, default=0)

    status = Column(Enum(InventoryStatusEnum), nullable=False)
    expiry_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    logs = relationship("InventoryLogModel", back_populates="item", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_non_negative"),
        CheckConstraint("on_order_quantity >= 0", name="ck_inventory_on_order_non_negative"),
        CheckConstraint("price >= 0", name="ck_inventory_price_non_negative"),
    )


class InventoryLogModel(Base):
    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True)
    # History survives item deletion (SET NULL) so analytics can be rebuilt.
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="SET NULL"), index=True)
    action = Column(String, nullable=False)
    quantity = Column(Integer, nullable=True)  # NULL for status_change
    detail = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    item = relationship("InventoryItemModel", back_populates="logs")

    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_inventory_log_quantity_positive"),
        Index("ix_inventory_logs_action_timestamp", "action", "timestamp"),
    )


# action -> analytics event type
_EVENTS = {
    InventoryAction.consume.value: "stock_consumed",
    InventoryAction.deliver.value: "stock_consumed",
    InventoryAction.return_.value: "stock_returned",
    InventoryAction.order.value: "purchase_order_created",
}


@event.listens_for(InventoryLogModel, "after_insert")
def outbox_after_inventory_log_insert(mapper, connection, target: InventoryLogModel):
    action = (target.action or "").strip().lower()
    event_type = _EVENTS.get(action)
    if event_type is None:
        return

    emit_event(
        connection,
        module="inventory",
        event_type=event_type,
        aggregate_type="inventory_log",
        aggregate_id=str(target.id),
        payload={
            "log_id": target.id,
            "item_id": target.item_id,
            "quantity": target.quantity,
            "date": ensure_utc(target.timestamp or utcnow()).isoformat(),
            "action": action,
        },
    )
