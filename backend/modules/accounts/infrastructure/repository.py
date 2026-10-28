from sqlalchemy import func
from datetime import datetime, timedelta
from backend.modules.accounts.domain.interfaces import AccountsRepositoryInterface
from backend.modules.accounts.infrastructure.models import TransactionModel


class SQLAlchemyAccountsRepository(AccountsRepositoryInterface):

    def __init__(self, db):
        self.db = db

    def create_transaction(self, transaction):
        model = TransactionModel(
            amount=transaction.amount,
            transaction_type=transaction.transaction_type,
            source_target=transaction.source_target,
            category=transaction.category,
            remarks=transaction.remarks
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def delete_transaction(self, transaction_id: int):
        model = self.db.query(TransactionModel).get(transaction_id)
        if model:
            self.db.delete(model)
            self.db.commit()

    def list_transactions(self):
        return self.db.query(TransactionModel).order_by(TransactionModel.date.desc()).all()

    def get_overall_summary(self):

        total_credit = self.db.query(func.sum(TransactionModel.amount)) \
            .filter(TransactionModel.transaction_type == "credit").scalar() or 0

        total_debit = self.db.query(func.sum(TransactionModel.amount)) \
            .filter(TransactionModel.transaction_type == "debit").scalar() or 0

        current_balance = total_credit - total_debit

        last_30_days = datetime.utcnow() - timedelta(days=30)

        last_30_credit = self.db.query(func.sum(TransactionModel.amount)) \
            .filter(
                TransactionModel.transaction_type == "credit",
                TransactionModel.date >= last_30_days
            ).scalar() or 0

        last_30_debit = self.db.query(func.sum(TransactionModel.amount)) \
            .filter(
                TransactionModel.transaction_type == "debit",
                TransactionModel.date >= last_30_days
            ).scalar() or 0

        net_last_30_days = last_30_credit - last_30_debit

        return {
            "current_balance": current_balance,
            "total_credit": total_credit,
            "total_debit": total_debit,
            "last_30_days_net": net_last_30_days
        }