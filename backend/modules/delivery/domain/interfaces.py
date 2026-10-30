from abc import ABC, abstractmethod


class DeliveryRepositoryInterface(ABC):

    @abstractmethod
    def create_delivery(self, order_id: str, customer_id: str, remarks: str | None):
        pass

    @abstractmethod
    def add_items(self, delivery_db_id: int, items: list[dict]):
        pass

    @abstractmethod
    def get_by_order_id(self, order_id: str, *, for_update: bool = False):
        pass

    @abstractmethod
    def list_deliveries(self, statuses: list[str], *, limit: int, offset: int):
        pass

    @abstractmethod
    def get_items(self, delivery_db_id: int):
        pass

    @abstractmethod
    def add_log(self, *, delivery_db_id: int, from_status: str | None, to_status: str, remark: str | None):
        pass

    @abstractmethod
    def get_logs(self, delivery_db_id: int):
        pass
