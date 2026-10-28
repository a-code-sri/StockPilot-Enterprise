from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class TransactionCreateDTO(BaseModel):
    amount: float
    transaction_type: Literal["credit", "debit"]
    source_target: str
    category: str
    remarks: str | None = None


class TransactionResponseDTO(BaseModel):
    id: int
    amount: float
    transaction_type: str
    source_target: str
    category: str
    remarks: str | None
    date: datetime

    class Config:
        from_attributes = True