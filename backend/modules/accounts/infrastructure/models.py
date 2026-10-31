import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, Index, Integer, Numeric, String, event

from backend.core.database.base import Base
from backend.core.time import ensure_utc, utcnow
from backend.outbox.repository import emit_event


class TransactionTypeEnum(str, enum.Enum):
    credit = "credit"
    debit = "debit"


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    amount = Column(Numeric(14, 2), nullable=False)
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False)
    source_target = Column(String, nullable=False)
    category = Column(String, nullable=False)
    remarks = Column(String)
    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_type_date", "transaction_type", "date"),
        Index("ix_transactions_category_type", "category", "transaction_type"),
        Index("ix_transactions_source_target", "source_target"),
    )


def tx_payload(tx: TransactionModel) -> dict:
    tt = tx.transaction_type
    return {
        "transaction_id": tx.id,
        "amount": str(tx.amount),  # string keeps Decimal precision through JSON
        "transaction_type": getattr(tt, "value", tt),
        "source_target": tx.source_target,
        "category": tx.category,
        "date": ensure_utc(tx.date).isoformat() if tx.date else None,
    }


@event.listens_for(TransactionModel, "after_insert")
def outbox_after_insert(mapper, connection, target: TransactionModel):
    emit_event(
        connection,
        module="accounts",
        event_type="transaction_created",
        aggregate_type="transaction",
        aggregate_id=str(target.id),
        payload=tx_payload(target),
    )


@event.listens_for(TransactionModel, "after_delete")
def outbox_after_delete(mapper, connection, target: TransactionModel):
    emit_event(
        connection,
        module="accounts",
        event_type="transaction_deleted",
        aggregate_type="transaction",
        aggregate_id=str(target.id),
        payload=tx_payload(target),
    )
