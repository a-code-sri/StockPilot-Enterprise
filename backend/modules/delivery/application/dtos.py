from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class DeliveryItemCreateDTO(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)


class DeliveryCreateDTO(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    customer_id: str = Field(min_length=1, max_length=80)
    items: List[DeliveryItemCreateDTO]
    remarks: Optional[str] = None


class DeliveryStatusUpdateDTO(BaseModel):
    status: Literal[
        "pending", "packed", "out_for_delivery", "delivered", "failed", "cancelled"
    ]
    remark: Optional[str] = None


class DeliveryListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    customer_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    items_count: int


class DeliveryDetailDTO(BaseModel):
    order_id: str
    customer_id: str
    status: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    items: list[dict]


class DeliveryLogDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: Optional[str]
    to_status: str
    remark: Optional[str]
    timestamp: datetime