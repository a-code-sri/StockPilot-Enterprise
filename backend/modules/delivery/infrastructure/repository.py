from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.core.time import utcnow
from backend.modules.delivery.domain.interfaces import DeliveryRepositoryInterface
from backend.modules.delivery.infrastructure.models import (
    DeliveryItemModel,
    DeliveryLogModel,
    DeliveryModel,
    DeliveryStatusEnum,
)


class SQLAlchemyDeliveryRepository(DeliveryRepositoryInterface):
    """Persistence only. Never commits: the service owns the transaction."""

    def __init__(self, db: Session):
        self.db = db

    def create_delivery(self, order_id: str, customer_id: str, remarks: str | None) -> DeliveryModel:
        now = utcnow()
        delivery = DeliveryModel(
            order_id=order_id,
            customer_id=customer_id,
            status=DeliveryStatusEnum.pending,
            remarks=remarks,
            created_at=now,
            updated_at=now,
        )
        self.db.add(delivery)
        self.db.flush()
        return delivery

    def get_by_order_id(self, order_id: str, *, for_update: bool = False) -> Optional[DeliveryModel]:
        stmt = select(DeliveryModel).where(DeliveryModel.order_id == order_id)
        if for_update:
            stmt = stmt.with_for_update()
        else:
            stmt = stmt.options(selectinload(DeliveryModel.items))
        return self.db.execute(stmt).scalars().first()

    def list_deliveries(self, statuses: list[str], *, limit: int, offset: int):
        base = select(DeliveryModel).where(DeliveryModel.status.in_(statuses))
        total = self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        rows = (
            self.db.execute(
                base.order_by(DeliveryModel.created_at.desc())
                .options(selectinload(DeliveryModel.items))
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def add_items(self, delivery_db_id: int, items: list[dict]) -> None:
        self.db.add_all(DeliveryItemModel(delivery_id=delivery_db_id, **item) for item in items)
        self.db.flush()

    def get_items(self, delivery_db_id: int) -> list[DeliveryItemModel]:
        stmt = select(DeliveryItemModel).where(DeliveryItemModel.delivery_id == delivery_db_id).order_by(DeliveryItemModel.id)
        return list(self.db.execute(stmt).scalars().all())

    def add_log(self, *, delivery_db_id: int, from_status: str | None, to_status: str, remark: str | None) -> DeliveryLogModel:
        log = DeliveryLogModel(
            delivery_id=delivery_db_id, from_status=from_status, to_status=to_status, remark=remark, timestamp=utcnow()
        )
        self.db.add(log)
        self.db.flush()
        return log

    def get_logs(self, delivery_db_id: int) -> list[DeliveryLogModel]:
        stmt = (
            select(DeliveryLogModel)
            .where(DeliveryLogModel.delivery_id == delivery_db_id)
            .order_by(DeliveryLogModel.timestamp.desc(), DeliveryLogModel.id.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
