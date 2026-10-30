from abc import ABC, abstractmethod


class AccountsRepositoryInterface(ABC):

    @abstractmethod
    def create_transaction(self, transaction):
        pass

    @abstractmethod
    def delete_transaction(self, transaction_id: int) -> bool:
        pass

    @abstractmethod
    def list_transactions(self, *, limit: int, offset: int, transaction_type=None, category=None):
        pass

    @abstractmethod
    def get_overall_summary(self):
        pass
