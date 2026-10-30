from sqlalchemy.orm import Session

from backend.modules.delivery.application.services import DeliveryService
from backend.modules.delivery.infrastructure.repository import SQLAlchemyDeliveryRepository


class DeliveryFacade:
    def __init__(self, db: Session):
        self.service = DeliveryService(SQLAlchemyDeliveryRepository(db))

    def create(self, dto):
        return self.service.create_delivery(dto)

    def list_active(self, *, limit: int, offset: int):
        return self.service.list_active(limit=limit, offset=offset)

    def list_finished(self, *, limit: int, offset: int):
        return self.service.list_finished(limit=limit, offset=offset)

    def get(self, order_id: str):
        return self.service.get_delivery(order_id)

    def items(self, order_id: str):
        return self.service.get_items(order_id)

    def update_status(self, order_id: str, status: str, remark: str | None):
        return self.service.update_status(order_id, status, remark)

    def logs(self, order_id: str):
        return self.service.get_logs(order_id)
