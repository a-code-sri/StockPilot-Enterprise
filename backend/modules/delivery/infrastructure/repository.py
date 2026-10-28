from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.modules.delivery.infrastructure.models import (
    DeliveryModel,
    DeliveryItemModel,
    DeliveryLogModel,
)


class SQLAlchemyDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---- Delivery ----

    def create_delivery(
        self,
        order_id: str,
        customer_id: str,
        status: str,
        remarks: str | None,
        *,
        commit: bool = True,
    ) -> DeliveryModel:
        delivery = DeliveryModel(
            order_id=order_id,
            customer_id=customer_id,
            status=status,
            remarks=remarks,
        )

        self.db.add(delivery)

        if commit:
            self.db.commit()
            self.db.refresh(delivery)

        return delivery

    def get_by_order_id(self, order_id: str) -> Optional[DeliveryModel]:
        stmt = (
            select(DeliveryModel)
            .where(DeliveryModel.order_id == order_id)
            .options(selectinload(DeliveryModel.items))
        )

        return self.db.execute(stmt).scalars().first()

    def list_deliveries(
        self,
        statuses: list[str],
    ) -> list[DeliveryModel]:
        stmt = (
            select(DeliveryModel)
            .where(DeliveryModel.status.in_(statuses))
            .order_by(DeliveryModel.created_at.desc())
            .options(selectinload(DeliveryModel.items))
        )

        return list(self.db.execute(stmt).scalars().all())

    def update_status(
        self,
        delivery: DeliveryModel,
        new_status: str,
        *,
        commit: bool = True,
    ) -> DeliveryModel:
        delivery.status = new_status
        delivery.updated_at = datetime.utcnow()

        self.db.add(delivery)

        if commit:
            self.db.commit()
            self.db.refresh(delivery)

        return delivery

    def set_completed(
        self,
        delivery: DeliveryModel,
        *,
        commit: bool = True,
    ) -> DeliveryModel:
        delivery.completed_at = datetime.utcnow()
        delivery.updated_at = datetime.utcnow()

        self.db.add(delivery)

        if commit:
            self.db.commit()
            self.db.refresh(delivery)

        return delivery

    # ---- Items ----

    def add_items(
        self,
        delivery_db_id: int,
        items: list[dict],
        *,
        commit: bool = True,
    ) -> None:
        rows = [
            DeliveryItemModel(
                delivery_id=delivery_db_id,
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
            for item in items
        ]

        self.db.add_all(rows)

        if commit:
            self.db.commit()

    def get_items(
        self,
        delivery_db_id: int,
    ) -> list[DeliveryItemModel]:
        stmt = (
            select(DeliveryItemModel)
            .where(DeliveryItemModel.delivery_id == delivery_db_id)
        )

        return list(self.db.execute(stmt).scalars().all())

    # ---- Logs ----

    def add_log(
        self,
        *,
        delivery_db_id: int,
        from_status: str | None,
        to_status: str,
        remark: str | None,
        timestamp: datetime | None = None,
        commit: bool = True,
    ) -> DeliveryLogModel:
        log = DeliveryLogModel(
            delivery_id=delivery_db_id,
            from_status=from_status,
            to_status=to_status,
            remark=remark,
            timestamp=timestamp or datetime.utcnow(),
        )

        self.db.add(log)

        if commit:
            self.db.commit()
            self.db.refresh(log)

        return log

    def get_logs(
        self,
        delivery_db_id: int,
    ) -> list[DeliveryLogModel]:
        stmt = (
            select(DeliveryLogModel)
            .where(DeliveryLogModel.delivery_id == delivery_db_id)
            .order_by(DeliveryLogModel.timestamp.desc())
        )

        return list(self.db.execute(stmt).scalars().all())