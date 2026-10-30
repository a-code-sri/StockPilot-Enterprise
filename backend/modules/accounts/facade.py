from backend.modules.accounts.application.services import AccountsService
from backend.modules.accounts.infrastructure.repository import SQLAlchemyAccountsRepository


class AccountsFacade:

    def __init__(self, db):
        self.service = AccountsService(SQLAlchemyAccountsRepository(db))

    def create_transaction(self, dto):
        return self.service.create_transaction(dto)

    def delete_transaction(self, transaction_id) -> bool:
        return self.service.delete_transaction(transaction_id)

    def list_transactions(self, **filters):
        return self.service.list_transactions(**filters)

    def get_summary(self):
        return self.service.get_summary()
