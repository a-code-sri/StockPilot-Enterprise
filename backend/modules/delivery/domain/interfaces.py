from abc import ABC, abstractmethod
from typing import Optional, List


class DeliveryRepositoryInterface(ABC):

    @abstractmethod
    def create_delivery(self, order_id: str, customer_id: str, status: str, remarks: str | None):
        pass

    @abstractmethod
    def add_items(self, delivery_db_id: int, items: list[dict]):
        pass

    @abstractmethod
    def get_by_order_id(self, order_id: str):
        pass

    @abstractmethod
    def list_deliveries(self, statuses: list[str]):
        pass

    @abstractmethod
    def update_status(self, delivery_model, new_status: str):
        pass

    @abstractmethod
    def set_completed(self, delivery_model):
        pass

    @abstractmethod
    def get_items(self, delivery_db_id: int):
        pass

    @abstractmethod
    def add_log(self, delivery_db_id: int, from_status: str | None, to_status: str, remark: str | None):
        pass

    @abstractmethod
    def get_logs(self, delivery_db_id: int):
        pass