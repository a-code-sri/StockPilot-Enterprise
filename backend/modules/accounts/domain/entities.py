from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class Transaction:

    def __init__(
        self,
        amount: float,
        transaction_type: TransactionType,
        source_target: str,
        category: str,
        remarks: str = ""
    ):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.amount = amount
        self.transaction_type = transaction_type
        self.source_target = source_target
        self.category = category
        self.remarks = remarks
        self.date = datetime.utcnow()