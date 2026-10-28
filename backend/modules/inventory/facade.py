from backend.modules.inventory.application.services import InventoryService
from backend.modules.inventory.infrastructure.repository import SQLAlchemyInventoryRepository


class InventoryFacade:

    def __init__(self, db):
        repository = SQLAlchemyInventoryRepository(db)
        self.service = InventoryService(repository)

    def create_inventory(self, dto):
        return self.service.create_inventory(dto)

    def update_inventory(self, name, dto):
        return self.service.update_inventory(name, dto)

    def update_status(self, name, status: str):
        return self.service.update_status(name, status)

    def list_inventory(self, status=None):
        return self.service.list_inventory(status)

    def delete_inventory(self, name):
        return self.service.delete_inventory(name)

    def get_inventory_logs(self, name):
        return self.service.get_inventory_logs(name)