from backend.modules.accounts.domain.entities import Transaction, TransactionType


class AccountsService:

    def __init__(self, repository):
        self.repository = repository

    def create_transaction(self, dto):
        transaction = Transaction(
            amount=dto.amount,
            transaction_type=TransactionType(dto.transaction_type),
            source_target=dto.source_target,
            category=dto.category,
            remarks=dto.remarks,
        )
        return self.repository.create_transaction(transaction)

    def delete_transaction(self, transaction_id: int) -> bool:
        return self.repository.delete_transaction(transaction_id)

    def list_transactions(self, *, limit: int, offset: int, transaction_type=None, category=None):
        return self.repository.list_transactions(
            limit=limit, offset=offset, transaction_type=transaction_type, category=category
        )

    def get_summary(self):
        return self.repository.get_overall_summary()
