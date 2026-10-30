from backend.modules.inventory.application.services import InventoryService
from backend.modules.inventory.infrastructure.repository import SQLAlchemyInventoryRepository


class InventoryFacade:
    """Public entry point to the inventory module (also used by the delivery module)."""

    def __init__(self, db):
        self.repository = SQLAlchemyInventoryRepository(db)
        self.service = InventoryService(self.repository)

    def create_inventory(self, dto):
        return self.service.create_inventory(dto)

    def get_item(self, item_id: int):
        return self.service.get_item(item_id)

    def update_inventory(self, item_id: int, dto):
        return self.service.update_inventory(item_id, dto)

    def update_status(self, item_id: int, status: str):
        return self.service.update_status(item_id, status)

    def list_inventory(self, **filters):
        return self.service.list_inventory(**filters)

    def delete_inventory(self, item_id: int):
        return self.service.delete_inventory(item_id)

    def get_inventory_logs(self, item_id: int):
        return self.service.get_inventory_logs(item_id)

    # ---- cross-module API (no commit; caller owns the transaction) ----

    def lock_item_by_name(self, name: str):
        return self.repository.get_item_by_name(name, for_update=True)

    def lock_item(self, item_id: int):
        return self.repository.get_item(item_id, for_update=True)

    def move_stock(self, model, action: str, quantity: int, note: str | None = None):
        return self.service.move_stock(model, action, quantity, note)
