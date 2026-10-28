from datetime import datetime, date
from enum import Enum
from typing import Optional


class InventoryStatus(str, Enum):
    UNDER_USE = "under_use"
    ORDERED = "ordered"
    CONSUMED = "consumed"


class InventoryItem:
    def __init__(
        self,
        name: str,
        quantity: int,
        price: float,
        status: InventoryStatus,
        on_order_quantity: int = 0,
        expiry_date: Optional[date] = None,
    ):
        self.name = name
        self.quantity = quantity
        self.price = price
        self.status = status
        self.on_order_quantity = on_order_quantity
        self.expiry_date = expiry_date
        self.created_at = datetime.utcnow()

    def increase_stock(self, amount: int):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.quantity += amount

    def decrease_stock(self, amount: int):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.quantity:
            raise ValueError("Insufficient stock")
        self.quantity -= amount

    def increase_on_order(self, amount: int):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.on_order_quantity += amount