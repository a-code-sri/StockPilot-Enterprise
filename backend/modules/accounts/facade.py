from backend.modules.accounts.infrastructure.repository import SQLAlchemyAccountsRepository
from backend.modules.accounts.application.services import AccountsService


class AccountsFacade:

    def __init__(self, db):
        repository = SQLAlchemyAccountsRepository(db)
        self.service = AccountsService(repository)

    def create_transaction(self, dto):
        return self.service.create_transaction(dto)

    def delete_transaction(self, transaction_id):
        return self.service.delete_transaction(transaction_id)

    def list_transactions(self):
        return self.service.list_transactions()

    def get_summary(self):
        return self.service.get_summary()