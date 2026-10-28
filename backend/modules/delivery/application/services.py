from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.modules.delivery.domain.entities import (
    DeliveryStatus,
    ACTIVE_STATUSES,
    FINISHED_STATUSES,
)


class DeliveryService:
    def __init__(self, repo):
        self.repo = repo

    def create_delivery(self, dto):
        existing = self.repo.get_by_order_id(dto.order_id)
        if existing:
            raise HTTPException(status_code=400, detail="order_id already exists.")

        if not dto.items or len(dto.items) == 0:
            raise HTTPException(status_code=400, detail="At least one cart item is required.")

        try:
            # ONE transaction for: delivery + items + creation log
            delivery = self.repo.create_delivery(
                order_id=dto.order_id.strip(),
                customer_id=dto.customer_id.strip(),
                status=DeliveryStatus.pending.value,
                remarks=dto.remarks,
                commit=False,
            )

            self.repo.add_items(
                delivery_db_id=delivery.id,
                items=[
                    {
                        "product_name": it.product_name.strip(),
                        "quantity": it.quantity,
                        "unit_price": it.unit_price,
                    }
                    for it in dto.items
                ],
                commit=False,
            )

            self.repo.add_log(
                delivery_db_id=delivery.id,
                from_status=None,
                to_status=delivery.status,
                remark="Delivery created",
                commit=False,
            )

            self.repo.db.commit()
            self.repo.db.refresh(delivery)
            return delivery

        except IntegrityError:
            self.repo.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity error while creating delivery (order_id must be unique, quantities/prices valid).",
            )
        except Exception as e:
            self.repo.db.rollback()
            raise

    def list_active(self):
        return self.repo.list_deliveries([s.value for s in ACTIVE_STATUSES])

    def list_finished(self):
        return self.repo.list_deliveries([s.value for s in FINISHED_STATUSES])

    def get_delivery(self, order_id: str):
        delivery = self.repo.get_by_order_id(order_id)
        if not delivery:
            raise HTTPException(status_code=404, detail="Delivery not found.")
        return delivery

    def get_items(self, order_id: str):
        delivery = self.get_delivery(order_id)
        return self.repo.get_items(delivery.id)

    def update_status(self, order_id: str, new_status: str, remark: str | None):
        delivery = self.get_delivery(order_id)

        current = delivery.status
        if current == new_status:
            return delivery

        try:
            _ = DeliveryStatus(new_status)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid status.")

        try:
            # ONE transaction for: status update (+ completed_at if finished) + log insert
            updated = self.repo.update_status(delivery, new_status, commit=False)

            if DeliveryStatus(new_status) in FINISHED_STATUSES:
                updated = self.repo.set_completed(updated, commit=False)

            self.repo.add_log(
                delivery_db_id=updated.id,
                from_status=current,
                to_status=new_status,
                remark=remark,
                commit=False,
            )

            # commit everything together (ensures delivered log -> outbox event is never missed)
            self.repo.db.commit()
            self.repo.db.refresh(updated)
            return updated

        except Exception:
            self.repo.db.rollback()
            raise

    def get_logs(self, order_id: str):
        delivery = self.get_delivery(order_id)
        return self.repo.get_logs(delivery.id)