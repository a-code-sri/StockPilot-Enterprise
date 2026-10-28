from backend.modules.inventory.domain.entities import InventoryItem, InventoryStatus
from backend.modules.inventory.infrastructure.models import InventoryStatusEnum


class InventoryService:

    def __init__(self, repository):
        self.repository = repository

    def create_inventory(self, dto):
        item = InventoryItem(
            name=dto.name.strip(),
            quantity=dto.quantity,
            on_order_quantity=dto.on_order_quantity,
            price=dto.price,
            status=InventoryStatus(dto.status),
            expiry_date=dto.expiry_date,
        )
        model = self.repository.create_item(item)

        # log initial stock if quantity > 0
        if dto.quantity > 0:
            self.repository.log_history({
                "item_id": model.id,
                "action": "add",
                "quantity": dto.quantity
            })

        # log initial on-order if any
        if dto.on_order_quantity > 0:
            self.repository.log_history({
                "item_id": model.id,
                "action": "order",
                "quantity": dto.on_order_quantity
            })

        return model

    def update_inventory(self, name: str, dto):
        model = self.repository.get_item_by_name(name)
        if not model:
            raise ValueError("Item not found")

        if dto.action == "add":
            model.quantity += dto.quantity

            if model.on_order_quantity > 0:
                model.on_order_quantity = max(0, model.on_order_quantity - dto.quantity)

        elif dto.action in ["consume", "deliver"]:
            if dto.quantity > model.quantity:
                raise ValueError("Insufficient stock")
            model.quantity -= dto.quantity

            if model.quantity == 0:
                model.status = InventoryStatusEnum.consumed

        elif dto.action == "order":
            model.on_order_quantity += dto.quantity

        # CRITICAL: keep update + log in ONE transaction
        try:
            self.repository.update_item(model, commit=False)
            self.repository.log_history({
                "item_id": model.id,
                "action": dto.action,
                "quantity": dto.quantity
            }, commit=False)

            self.repository.db.commit()
            self.repository.db.refresh(model)
        except Exception:
            self.repository.db.rollback()
            raise

        return model

    def update_status(self, name: str, status: str):
        model = self.repository.get_item_by_name(name)
        if not model:
            raise ValueError("Item not found")

        model.status = InventoryStatusEnum(status)

        # keep update + log atomic
        try:
            self.repository.update_item(model, commit=False)
            self.repository.log_history({
                "item_id": model.id,
                "action": "status_change",
                "quantity": 1
            }, commit=False)

            self.repository.db.commit()
            self.repository.db.refresh(model)
        except Exception:
            self.repository.db.rollback()
            raise

        return model

    def list_inventory(self, status: str = None):
        return self.repository.list_items(status)

    def delete_inventory(self, name: str):
        model = self.repository.get_item_by_name(name)
        if not model:
            raise ValueError("Item not found")
        self.repository.delete_item(model)

    def get_inventory_logs(self, name: str):
        model = self.repository.get_item_by_name(name)
        if not model:
            raise ValueError("Item not found")
        return self.repository.get_logs(model.id)