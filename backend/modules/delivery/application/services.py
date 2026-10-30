from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.core.time import utcnow
from backend.modules.delivery.domain.entities import (
    ACTIVE_STATUSES,
    DEDUCT_STOCK_ON,
    FINISHED_STATUSES,
    RETURN_STOCK_ON,
    DeliveryStatus,
    InvalidTransition,
    check_transition,
)
from backend.modules.delivery.infrastructure.models import DeliveryStatusEnum
from backend.modules.inventory.domain.entities import InventoryError
from backend.modules.inventory.facade import InventoryFacade


def _status_value(s) -> str:
    return getattr(s, "value", s)


class DeliveryService:
    def __init__(self, repo):
        self.repo = repo
        self.db = repo.db
        self.inventory = InventoryFacade(self.db)

    def _resolve_inventory_link(self, item) -> int | None:
        if item.inventory_item_id is not None:
            if not self.inventory.repository.get_item(item.inventory_item_id):
                raise HTTPException(status_code=400, detail=f"Inventory item {item.inventory_item_id} does not exist.")
            return item.inventory_item_id
        match = self.inventory.repository.get_item_by_name(item.product_name.strip())
        return match.id if match else None

    def create_delivery(self, dto):
        order_id = dto.order_id.strip()
        if self.repo.get_by_order_id(order_id):
            raise HTTPException(status_code=409, detail="order_id already exists.")

        try:
            delivery = self.repo.create_delivery(order_id, dto.customer_id.strip(), dto.remarks)
            self.repo.add_items(
                delivery.id,
                [
                    {
                        "product_name": it.product_name.strip(),
                        "quantity": it.quantity,
                        "unit_price": it.unit_price,
                        "inventory_item_id": self._resolve_inventory_link(it),
                    }
                    for it in dto.items
                ],
            )
            self.repo.add_log(
                delivery_db_id=delivery.id, from_status=None, to_status=DeliveryStatus.pending.value,
                remark="Delivery created",
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="order_id must be unique.")
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(delivery)
        return delivery

    def list_active(self, *, limit: int, offset: int):
        return self.repo.list_deliveries([s.value for s in ACTIVE_STATUSES], limit=limit, offset=offset)

    def list_finished(self, *, limit: int, offset: int):
        return self.repo.list_deliveries([s.value for s in FINISHED_STATUSES], limit=limit, offset=offset)

    def get_delivery(self, order_id: str, *, for_update: bool = False):
        delivery = self.repo.get_by_order_id(order_id, for_update=for_update)
        if not delivery:
            raise HTTPException(status_code=404, detail="Delivery not found.")
        return delivery

    def get_items(self, order_id: str):
        return self.repo.get_items(self.get_delivery(order_id).id)

    def _move_linked_stock(self, delivery, action: str) -> None:
        """Deduct ('deliver') or restore ('return') stock for every linked item, locking rows in id order."""
        items = sorted(
            (i for i in self.repo.get_items(delivery.id) if i.inventory_item_id is not None),
            key=lambda i: i.inventory_item_id,
        )
        for item in items:
            stock = self.inventory.lock_item(item.inventory_item_id)
            if stock is None:
                continue  # inventory item was deleted; nothing to adjust
            self.inventory.move_stock(stock, action, item.quantity, f"Delivery {delivery.order_id}")

    def update_status(self, order_id: str, new_status: str, remark: str | None):
        try:
            delivery = self.get_delivery(order_id, for_update=True)
            current = _status_value(delivery.status)
            if current == new_status:
                return delivery

            check_transition(current, new_status)
            target = DeliveryStatus(new_status)

            if target == DEDUCT_STOCK_ON and not delivery.stock_deducted:
                self._move_linked_stock(delivery, "deliver")
                delivery.stock_deducted = True
            elif target in RETURN_STOCK_ON and delivery.stock_deducted:
                self._move_linked_stock(delivery, "return")
                delivery.stock_deducted = False

            now = utcnow()
            delivery.status = DeliveryStatusEnum(new_status)
            delivery.updated_at = now
            delivery.completed_at = now if target in FINISHED_STATUSES else None

            # Same transaction as the status change, so the analytics event is never lost.
            self.repo.add_log(delivery_db_id=delivery.id, from_status=current, to_status=new_status, remark=remark)
            self.db.commit()
        except InvalidTransition as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except InventoryError as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot dispatch: {e}")
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(delivery)
        return delivery

    def get_logs(self, order_id: str):
        return self.repo.get_logs(self.get_delivery(order_id).id)
