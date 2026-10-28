import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Index, event
from sqlalchemy.sql import insert

from backend.core.database.base import Base
from backend.outbox.models import AnalyticsOutbox


class TransactionTypeEnum(str, enum.Enum):
    credit = "credit"
    debit = "debit"


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False)
    source_target = Column(String, nullable=False)
    category = Column(String, nullable=False)
    remarks = Column(String)
    date = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_type_date", "transaction_type", "date"),
        Index("ix_transactions_category_type", "category", "transaction_type"),
        Index("ix_transactions_source_target", "source_target"),
    )


def _tx_payload(tx: TransactionModel) -> dict:
    # Keep payload JSON-friendly and analytics-focused
    dt = tx.date
    if isinstance(dt, datetime):
        # ensure ISO string; keep as-is if naive
        date_str = dt.isoformat()
    else:
        date_str = None

    tt = tx.transaction_type
    if hasattr(tt, "value"):
        tt = tt.value

    return {
        "transaction_id": tx.id,
        "amount": tx.amount,
        "transaction_type": tt,
        "source_target": tx.source_target,
        "category": tx.category,
        "remarks": tx.remarks,
        "date": date_str,
    }


@event.listens_for(TransactionModel, "after_insert")
def outbox_after_insert(mapper, connection, target: TransactionModel):
    payload = _tx_payload(target)
    connection.execute(
        insert(AnalyticsOutbox).values(
            module="accounts",
            event_type="transaction_created",
            aggregate_type="transaction",
            aggregate_id=str(target.id),
            payload=payload,
            status="pending",
            available_at=datetime.now(timezone.utc),
        )
    )


@event.listens_for(TransactionModel, "after_delete")
def outbox_after_delete(mapper, connection, target: TransactionModel):
    payload = _tx_payload(target)
    connection.execute(
        insert(AnalyticsOutbox).values(
            module="accounts",
            event_type="transaction_deleted",
            aggregate_type="transaction",
            aggregate_id=str(target.id),
            payload=payload,
            status="pending",
            available_at=datetime.now(timezone.utc),
        )
    )