from datetime import timedelta
from decimal import Decimal

from sqlalchemy import case, func

from backend.core.time import utcnow
from backend.modules.accounts.domain.interfaces import AccountsRepositoryInterface
from backend.modules.accounts.infrastructure.models import TransactionModel, TransactionTypeEnum


class SQLAlchemyAccountsRepository(AccountsRepositoryInterface):

    def __init__(self, db):
        self.db = db

    def create_transaction(self, transaction):
        model = TransactionModel(
            amount=transaction.amount,
            transaction_type=TransactionTypeEnum(transaction.transaction_type.value),
            source_target=transaction.source_target,
            category=transaction.category,
            remarks=transaction.remarks,
            date=transaction.date,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def delete_transaction(self, transaction_id: int) -> bool:
        model = self.db.get(TransactionModel, transaction_id)
        if not model:
            return False
        self.db.delete(model)
        self.db.commit()
        return True

    def list_transactions(self, *, limit: int, offset: int, transaction_type=None, category=None):
        query = self.db.query(TransactionModel)
        if transaction_type:
            query = query.filter(TransactionModel.transaction_type == transaction_type)
        if category:
            query = query.filter(TransactionModel.category == category)
        total = query.count()
        rows = (
            query.order_by(TransactionModel.date.desc(), TransactionModel.id.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return rows, total

    def get_overall_summary(self):
        since = utcnow() - timedelta(days=30)
        is_credit = TransactionModel.transaction_type == TransactionTypeEnum.credit
        is_debit = TransactionModel.transaction_type == TransactionTypeEnum.debit
        recent = TransactionModel.date >= since

        def _sum(cond):
            return func.coalesce(func.sum(case((cond, TransactionModel.amount), else_=0)), 0)

        total_credit, total_debit, credit_30, debit_30 = self.db.query(
            _sum(is_credit), _sum(is_debit), _sum(is_credit & recent), _sum(is_debit & recent)
        ).one()

        total_credit, total_debit = Decimal(total_credit), Decimal(total_debit)
        return {
            "current_balance": float(total_credit - total_debit),
            "total_credit": float(total_credit),
            "total_debit": float(total_debit),
            "last_30_days_net": float(Decimal(credit_30) - Decimal(debit_30)),
        }
