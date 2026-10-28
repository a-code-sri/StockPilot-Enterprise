from abc import ABC, abstractmethod


class AccountsRepositoryInterface(ABC):

    @abstractmethod
    def create_transaction(self, transaction):
        pass

    @abstractmethod
    def delete_transaction(self, transaction_id: int):
        pass

    @abstractmethod
    def list_transactions(self):
        pass

    @abstractmethod
    def get_overall_summary(self):
        pass