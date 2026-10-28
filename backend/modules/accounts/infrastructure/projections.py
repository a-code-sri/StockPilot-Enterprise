from sqlalchemy import Column, Date, DateTime, Numeric, String, Index, PrimaryKeyConstraint
from sqlalchemy.sql import func

from backend.core.database.base import Base


class AccountsDailyTotals(Base):
    __tablename__ = "accounts_daily_totals"

    day = Column(Date, primary_key=True)  # bucket by day
    income = Column(Numeric(14, 2), nullable=False, server_default="0")
    expenses = Column(Numeric(14, 2), nullable=False, server_default="0")

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_accounts_daily_totals_day", "day"),
    )


class AccountsDailyCategoryTotals(Base):
    __tablename__ = "accounts_daily_category_totals"

    day = Column(Date, nullable=False)
    category = Column(String, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # "credit" or "debit"
    amount = Column(Numeric(14, 2), nullable=False, server_default="0")

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("day", "category", "transaction_type", name="pk_accounts_daily_category_totals"),
        Index("ix_accounts_daily_category_totals_day", "day"),
        Index("ix_accounts_daily_category_totals_category", "category"),
        Index("ix_accounts_daily_category_totals_type", "transaction_type"),
    )