from decimal import Decimal
from enum import Enum

from backend.core.time import utcnow


class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class Transaction:

    def __init__(
        self,
        amount: Decimal,
        transaction_type: TransactionType,
        source_target: str,
        category: str,
        remarks: str | None = None,
    ):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.amount = amount
        self.transaction_type = transaction_type
        self.source_target = source_target.strip()
        self.category = category.strip()
        self.remarks = remarks
        self.date = utcnow()
