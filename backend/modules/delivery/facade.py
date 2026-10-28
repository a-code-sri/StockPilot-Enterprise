from sqlalchemy.orm import Session
from backend.modules.delivery.infrastructure.repository import SQLAlchemyDeliveryRepository
from backend.modules.delivery.application.services import DeliveryService


class DeliveryFacade:
    def __init__(self, db: Session):
        repo = SQLAlchemyDeliveryRepository(db)
        self.service = DeliveryService(repo)

    def create(self, dto):
        return self.service.create_delivery(dto)

    def list_active(self):
        return self.service.list_active()

    def list_finished(self):
        return self.service.list_finished()

    def get(self, order_id: str):
        return self.service.get_delivery(order_id)

    def items(self, order_id: str):
        return self.service.get_items(order_id)

    def update_status(self, order_id: str, status: str, remark: str | None):
        return self.service.update_status(order_id, status, remark)

    def logs(self, order_id: str):
        return self.service.get_logs(order_id)