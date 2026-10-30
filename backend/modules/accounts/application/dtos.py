from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class TransactionCreateDTO(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    transaction_type: Literal["credit", "debit"]
    source_target: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    remarks: str | None = Field(default=None, max_length=1000)


class TransactionResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    transaction_type: str
    source_target: str
    category: str
    remarks: str | None
    date: datetime

    @field_serializer("amount")
    def _amount(self, v: Decimal) -> float:
        # The web UI does arithmetic on amounts; send a JSON number.
        return float(v)

    @field_serializer("transaction_type")
    def _ttype(self, v) -> str:
        return getattr(v, "value", v)
