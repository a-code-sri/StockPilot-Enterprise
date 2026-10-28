from abc import ABC, abstractmethod


class InventoryRepositoryInterface(ABC):

    @abstractmethod
    def create_item(self, item):
        pass

    @abstractmethod
    def get_item_by_name(self, name: str):
        pass

    @abstractmethod
    def update_item(self, item):
        pass

    @abstractmethod
    def log_history(self, log):
        pass
    @abstractmethod
    def list_items(self, status: str = None):
        pass

    @abstractmethod
    def delete_item(self, model):
        pass

    @abstractmethod
    def get_logs(self, item_id: int):
        pass