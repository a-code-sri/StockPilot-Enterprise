from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class InventoryCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=0)
    on_order_quantity: int = Field(default=0, ge=0)
    price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    status: Literal["under_use", "ordered", "consumed"]
    expiry_date: Optional[date] = None


class InventoryUpdateDTO(BaseModel):
    """A stock movement."""

    quantity: int = Field(gt=0)
    action: Literal["add", "consume", "deliver", "order", "return"]
    note: Optional[str] = Field(default=None, max_length=500)


class InventoryStatusUpdateDTO(BaseModel):
    status: Literal["under_use", "ordered", "consumed"]


class InventoryResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: int
    on_order_quantity: int
    price: Decimal
    status: str
    expiry_date: Optional[date] = None
    created_at: datetime

    @field_serializer("price")
    def _price(self, v: Decimal) -> float:
        return float(v)

    @field_serializer("status")
    def _status(self, v) -> str:
        return getattr(v, "value", v)


class InventoryLogDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    quantity: Optional[int]
    detail: Optional[str] = None
    timestamp: datetime
