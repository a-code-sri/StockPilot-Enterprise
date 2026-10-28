from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class DeliveryStatus(str, Enum):
    pending = "pending"
    packed = "packed"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    cancelled = "cancelled"


ACTIVE_STATUSES = {
    DeliveryStatus.pending,
    DeliveryStatus.packed,
    DeliveryStatus.out_for_delivery,
}

FINISHED_STATUSES = {
    DeliveryStatus.delivered,
    DeliveryStatus.failed,
    DeliveryStatus.cancelled,
}


@dataclass(frozen=True)
class DeliveryItemEntity:
    product_name: str
    quantity: int
    unit_price: float = 0.0


@dataclass(frozen=True)
class DeliveryCreateEntity:
    order_id: str
    customer_id: str
    items: List[DeliveryItemEntity]
    created_at: datetime
    remarks: Optional[str] = None