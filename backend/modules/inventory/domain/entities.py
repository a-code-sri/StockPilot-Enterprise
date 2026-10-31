"""
Inventory domain rules, kept free of persistence so they are unit-testable.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class InventoryStatus(str, Enum):
    UNDER_USE = "under_use"
    ORDERED = "ordered"
    CONSUMED = "consumed"


class InventoryError(ValueError):
    """Business-rule violation (maps to HTTP 400)."""


@dataclass
class InventoryItem:
    name: str
    quantity: int
    price: Decimal
    status: InventoryStatus
    on_order_quantity: int = 0
    expiry_date: Optional[date] = None


@dataclass(frozen=True)
class StockLevels:
    quantity: int
    on_order_quantity: int
    becomes_consumed: bool = False


def apply_movement(quantity: int, on_order: int, action: str, amount: int) -> StockLevels:
    """
    Pure stock arithmetic for one movement. Raises InventoryError on invalid input.

    add      -> stock +amount; fulfils on-order quantity first
    consume  -> stock -amount (must be available)
    deliver  -> same as consume
    return   -> stock +amount (does not touch on-order)
    order    -> on-order +amount
    """
    if amount <= 0:
        raise InventoryError("Quantity must be positive")

    if action == "add":
        return StockLevels(quantity + amount, max(0, on_order - amount))
    if action in ("consume", "deliver"):
        if amount > quantity:
            raise InventoryError(f"Insufficient stock: requested {amount}, available {quantity}")
        remaining = quantity - amount
        return StockLevels(remaining, on_order, becomes_consumed=(remaining == 0))
    if action == "return":
        return StockLevels(quantity + amount, on_order)
    if action == "order":
        return StockLevels(quantity, on_order + amount)
    raise InventoryError(f"Unknown action '{action}'")
