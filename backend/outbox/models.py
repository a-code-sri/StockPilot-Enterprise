from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from backend.core.database.base import Base


class AnalyticsOutbox(Base):
    """
    Transactional outbox for analytics events.

    Insert rows into this table IN THE SAME DB TRANSACTION as your business write.
    A background worker will later read/process these rows and update analytics projections.
    """
    __tablename__ = "analytics_outbox"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)

    module = Column(String(50), nullable=False, index=True)        # e.g. "accounts"
    event_type = Column(String(100), nullable=False, index=True)   # e.g. "transaction_created"

    # Optional metadata (useful later, not required)
    aggregate_type = Column(String(100), nullable=True, index=True)
    aggregate_id = Column(String(100), nullable=True, index=True)

    payload = Column(JSONB, nullable=False)

    # Status lifecycle: pending -> processing -> done
    # On error: processing -> failed (retryable)
    status = Column(String(20), nullable=False, index=True, server_default="pending")

    attempts = Column(Integer, nullable=False, server_default="0")
    last_error = Column(Text, nullable=True)

    available_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_outbox_status_available_created", "status", "available_at", "created_at"),
    )