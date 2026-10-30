from abc import ABC, abstractmethod


class InventoryRepositoryInterface(ABC):

    @abstractmethod
    def add_item(self, item):
        pass

    @abstractmethod
    def get_item(self, item_id: int, *, for_update: bool = False):
        pass

    @abstractmethod
    def get_item_by_name(self, name: str, *, for_update: bool = False):
        pass

    @abstractmethod
    def add_log(self, item_id: int, action: str, quantity, detail=None):
        pass

    @abstractmethod
    def list_items(self, *, status=None, search=None, limit: int, offset: int):
        pass

    @abstractmethod
    def delete_item(self, model):
        pass

    @abstractmethod
    def get_logs(self, item_id: int, *, limit: int):
        pass
