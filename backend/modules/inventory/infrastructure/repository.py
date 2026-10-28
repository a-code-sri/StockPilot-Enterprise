from backend.modules.inventory.domain.interfaces import InventoryRepositoryInterface
from backend.modules.inventory.infrastructure.models import (
    InventoryItemModel,
    InventoryLogModel,
    InventoryStatusEnum,
)


class SQLAlchemyInventoryRepository(InventoryRepositoryInterface):

    def __init__(self, db):
        self.db = db

    def create_item(self, item):
        model = InventoryItemModel(
            name=item.name,
            quantity=item.quantity,
            on_order_quantity=item.on_order_quantity,
            price=item.price,
            status=InventoryStatusEnum(item.status.value),
            expiry_date=item.expiry_date,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def get_item_by_name(self, name: str):
        return self.db.query(InventoryItemModel).filter_by(name=name).first()

    def update_item(self, model, commit: bool = True):
        """
        If commit=False, caller is responsible for committing.
        This is necessary to keep item update + log insert in the same transaction.
        """
        if commit:
            self.db.commit()
            self.db.refresh(model)
        else:
            self.db.flush()
        return model

    def log_history(self, log_data, commit: bool = True):
        """
        If commit=False, caller is responsible for committing.
        """
        log = InventoryLogModel(**log_data)
        self.db.add(log)
        if commit:
            self.db.commit()
            self.db.refresh(log)
        else:
            self.db.flush()
        return log

    def list_items(self, status: str = None):
        query = self.db.query(InventoryItemModel)
        if status:
            query = query.filter(InventoryItemModel.status == status)
        return query.all()

    def delete_item(self, model):
        self.db.delete(model)
        self.db.commit()

    def get_logs(self, item_id: int):
        return (
            self.db.query(InventoryLogModel)
            .filter_by(item_id=item_id)
            .order_by(InventoryLogModel.timestamp.desc())
            .all()
        )