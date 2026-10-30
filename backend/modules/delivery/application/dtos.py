from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DeliveryItemCreateDTO(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    # Link to an inventory item. If omitted, an inventory item with exactly the
    # same name is linked automatically; unlinked items do not touch stock.
    inventory_item_id: Optional[int] = None


class DeliveryCreateDTO(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    customer_id: str = Field(min_length=1, max_length=80)
    items: List[DeliveryItemCreateDTO] = Field(min_length=1)
    remarks: Optional[str] = Field(default=None, max_length=1000)


class DeliveryStatusUpdateDTO(BaseModel):
    status: Literal["pending", "packed", "out_for_delivery", "delivered", "failed", "cancelled"]
    remark: Optional[str] = Field(default=None, max_length=1000)


class DeliveryListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    customer_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    items_count: int
    allowed_next: List[str] = []


class DeliveryItemDTO(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    inventory_item_id: Optional[int] = None


class DeliveryDetailDTO(BaseModel):
    order_id: str
    customer_id: str
    status: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    stock_deducted: bool = False
    allowed_next: List[str] = []
    items: List[DeliveryItemDTO]


class DeliveryLogDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: Optional[str]
    to_status: str
    remark: Optional[str]
    timestamp: datetime
