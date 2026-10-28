from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.modules.accounts.infrastructure.models import TransactionModel


class AccountsAnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def totals_for_window(self, days: int):
        since = datetime.utcnow() - timedelta(days=days)

        total_credit = (
            self.db.query(func.sum(TransactionModel.amount))
            .filter(
                TransactionModel.transaction_type == "credit",
                TransactionModel.date >= since,
            )
            .scalar()
            or 0.0
        )

        total_debit = (
            self.db.query(func.sum(TransactionModel.amount))
            .filter(
                TransactionModel.transaction_type == "debit",
                TransactionModel.date >= since,
            )
            .scalar()
            or 0.0
        )

        return {
            "days": days,
            "total_credit": float(total_credit),
            "total_debit": float(total_debit),
            "net": float(total_credit - total_debit),
        }

    def totals_all_time(self):
        total_credit = (
            self.db.query(func.sum(TransactionModel.amount))
            .filter(TransactionModel.transaction_type == "credit")
            .scalar()
            or 0.0
        )

        total_debit = (
            self.db.query(func.sum(TransactionModel.amount))
            .filter(TransactionModel.transaction_type == "debit")
            .scalar()
            or 0.0
        )

        return {
            "total_credit": float(total_credit),
            "total_debit": float(total_debit),
            "current_balance": float(total_credit - total_debit),
        }

    def distribution_by_category(self, days: int, transaction_type: str):
        since = datetime.utcnow() - timedelta(days=days)

        rows = (
            self.db.query(
                TransactionModel.category,
                func.sum(TransactionModel.amount).label("amount"),
            )
            .filter(
                TransactionModel.transaction_type == transaction_type,
                TransactionModel.date >= since,
            )
            .group_by(TransactionModel.category)
            .order_by(func.sum(TransactionModel.amount).desc())
            .all()
        )

        return [
            {"category": r.category, "amount": float(r.amount or 0.0)}
            for r in rows
        ]

    def top_sources_targets(self, days: int, top_n: int):
        since = datetime.utcnow() - timedelta(days=days)

        # Top income sources: credits grouped by source_target
        income_rows = (
            self.db.query(
                TransactionModel.source_target,
                func.sum(TransactionModel.amount).label("amount"),
            )
            .filter(
                TransactionModel.transaction_type == "credit",
                TransactionModel.date >= since,
            )
            .group_by(TransactionModel.source_target)
            .order_by(func.sum(TransactionModel.amount).desc())
            .limit(top_n)
            .all()
        )

        # Top expense targets: debits grouped by source_target
        expense_rows = (
            self.db.query(
                TransactionModel.source_target,
                func.sum(TransactionModel.amount).label("amount"),
            )
            .filter(
                TransactionModel.transaction_type == "debit",
                TransactionModel.date >= since,
            )
            .group_by(TransactionModel.source_target)
            .order_by(func.sum(TransactionModel.amount).desc())
            .limit(top_n)
            .all()
        )

        return {
            "top_income_sources": [
                {"source": r.source_target, "amount": float(r.amount or 0.0)}
                for r in income_rows
            ],
            "top_expense_targets": [
                {"target": r.source_target, "amount": float(r.amount or 0.0)}
                for r in expense_rows
            ],
        }