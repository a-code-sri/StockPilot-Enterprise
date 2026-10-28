from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime, date


class InventoryCreateDTO(BaseModel):
    name: str
    quantity: int = Field(ge=0)
    on_order_quantity: int = Field(default=0, ge=0)
    price: float = Field(default=0.0, ge=0)
    status: Literal["under_use", "ordered", "consumed"]
    expiry_date: Optional[date] = None


class InventoryUpdateDTO(BaseModel):
    quantity: int = Field(gt=0)
    action: Literal["add", "consume", "deliver", "order"]


class InventoryStatusUpdateDTO(BaseModel):
    status: Literal["under_use", "ordered", "consumed"]


class InventoryResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: int
    on_order_quantity: int
    price: float
    status: str
    expiry_date: Optional[date] = None
    created_at: datetime


class InventoryLogDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    quantity: int
    timestamp: datetime