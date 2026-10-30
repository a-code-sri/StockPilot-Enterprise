from sqlalchemy.exc import IntegrityError

from backend.modules.inventory.domain.entities import (
    InventoryError,
    InventoryItem,
    InventoryStatus,
    apply_movement,
)
from backend.modules.inventory.infrastructure.models import InventoryStatusEnum


class InventoryNotFound(LookupError):
    pass


class InventoryConflict(Exception):
    pass


class InventoryService:

    def __init__(self, repository):
        self.repository = repository
        self.db = repository.db

    def _commit(self):
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise InventoryConflict("An inventory item with this name already exists") from e

    def _require(self, item_id: int, *, for_update: bool = False):
        model = self.repository.get_item(item_id, for_update=for_update)
        if not model:
            raise InventoryNotFound(f"Inventory item {item_id} not found")
        return model

    def create_inventory(self, dto):
        name = dto.name.strip()
        if self.repository.get_item_by_name(name):
            raise InventoryConflict(f"An inventory item named '{name}' already exists")

        item = InventoryItem(
            name=name,
            quantity=dto.quantity,
            on_order_quantity=dto.on_order_quantity,
            price=dto.price,
            status=InventoryStatus(dto.status),
            expiry_date=dto.expiry_date,
        )
        try:
            model = self.repository.add_item(item)
            # Opening balances are logged in the same transaction as the item.
            if dto.quantity > 0:
                self.repository.add_log(model.id, "add", dto.quantity, "Opening stock")
            if dto.on_order_quantity > 0:
                self.repository.add_log(model.id, "order", dto.on_order_quantity, "Opening on-order quantity")
        except IntegrityError as e:
            self.db.rollback()
            raise InventoryConflict(f"An inventory item named '{name}' already exists") from e
        except Exception:
            self.db.rollback()
            raise
        self._commit()
        self.db.refresh(model)
        return model

    def move_stock(self, model, action: str, quantity: int, note: str | None = None):
        """
        Apply a movement to an already-locked item WITHOUT committing. Used by the
        delivery module so stock changes commit atomically with delivery status.
        """
        levels = apply_movement(model.quantity, model.on_order_quantity, action, quantity)
        model.quantity = levels.quantity
        model.on_order_quantity = levels.on_order_quantity
        if levels.becomes_consumed:
            model.status = InventoryStatusEnum.consumed
        elif action in ("add", "return") and model.status == InventoryStatusEnum.consumed:
            model.status = InventoryStatusEnum.under_use
        self.repository.add_log(model.id, action, quantity, note)
        return model

    def update_inventory(self, item_id: int, dto):
        try:
            model = self._require(item_id, for_update=True)
            self.move_stock(model, dto.action, dto.quantity, dto.note)
        except Exception:
            self.db.rollback()
            raise
        self._commit()
        self.db.refresh(model)
        return model

    def update_status(self, item_id: int, status: str):
        try:
            model = self._require(item_id, for_update=True)
            old = model.status.value if hasattr(model.status, "value") else model.status
            if old != status:
                model.status = InventoryStatusEnum(status)
                self.repository.add_log(model.id, "status_change", None, f"{old} -> {status}")
        except Exception:
            self.db.rollback()
            raise
        self._commit()
        self.db.refresh(model)
        return model

    def get_item(self, item_id: int):
        return self._require(item_id)

    def list_inventory(self, *, status=None, search=None, limit: int, offset: int):
        return self.repository.list_items(status=status, search=search, limit=limit, offset=offset)

    def delete_inventory(self, item_id: int) -> None:
        model = self._require(item_id)
        self.repository.delete_item(model)
        self.db.commit()

    def get_inventory_logs(self, item_id: int, limit: int = 200):
        self._require(item_id)
        return self.repository.get_logs(item_id, limit=limit)


__all__ = ["InventoryService", "InventoryNotFound", "InventoryConflict", "InventoryError"]
