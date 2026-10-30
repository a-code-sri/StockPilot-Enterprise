from backend.modules.inventory.domain.interfaces import InventoryRepositoryInterface
from backend.modules.inventory.infrastructure.models import (
    InventoryItemModel,
    InventoryLogModel,
    InventoryStatusEnum,
)


class SQLAlchemyInventoryRepository(InventoryRepositoryInterface):
    """Persistence only. Never commits: the service owns the transaction."""

    def __init__(self, db):
        self.db = db

    def add_item(self, item) -> InventoryItemModel:
        model = InventoryItemModel(
            name=item.name,
            quantity=item.quantity,
            on_order_quantity=item.on_order_quantity,
            price=item.price,
            status=InventoryStatusEnum(item.status.value),
            expiry_date=item.expiry_date,
        )
        self.db.add(model)
        self.db.flush()
        return model

    def _query(self, for_update: bool):
        q = self.db.query(InventoryItemModel)
        # Row lock prevents lost updates when two requests move the same stock.
        return q.with_for_update() if for_update else q

    def get_item(self, item_id: int, *, for_update: bool = False):
        return self._query(for_update).filter(InventoryItemModel.id == item_id).first()

    def get_item_by_name(self, name: str, *, for_update: bool = False):
        return self._query(for_update).filter(InventoryItemModel.name == name).first()

    def add_log(self, item_id: int, action: str, quantity, detail=None) -> InventoryLogModel:
        log = InventoryLogModel(item_id=item_id, action=action, quantity=quantity, detail=detail)
        self.db.add(log)
        self.db.flush()
        return log

    def list_items(self, *, status=None, search=None, limit: int, offset: int):
        query = self.db.query(InventoryItemModel)
        if status:
            query = query.filter(InventoryItemModel.status == status)
        if search:
            query = query.filter(InventoryItemModel.name.ilike(f"%{search}%"))
        total = query.count()
        rows = query.order_by(InventoryItemModel.name.asc()).limit(limit).offset(offset).all()
        return rows, total

    def delete_item(self, model) -> None:
        self.db.delete(model)
        self.db.flush()

    def get_logs(self, item_id: int, *, limit: int):
        return (
            self.db.query(InventoryLogModel)
            .filter(InventoryLogModel.item_id == item_id)
            .order_by(InventoryLogModel.timestamp.desc(), InventoryLogModel.id.desc())
            .limit(limit)
            .all()
        )
