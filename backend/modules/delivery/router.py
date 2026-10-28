from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission

from backend.modules.delivery.facade import DeliveryFacade
from backend.modules.delivery.application.dtos import (
    DeliveryCreateDTO,
    DeliveryStatusUpdateDTO,
    DeliveryListDTO,
    DeliveryDetailDTO,
    DeliveryLogDTO,
)

router = APIRouter()


@router.post("/")
def create_delivery(
    dto: DeliveryCreateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("delivery.write")),
):
    facade = DeliveryFacade(db)
    delivery = facade.create(dto)
    return {"message": "Delivery created", "order_id": delivery.order_id}


@router.get("/active", response_model=list[DeliveryListDTO])
def list_active_deliveries(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("delivery.read")),
):
    facade = DeliveryFacade(db)
    rows = facade.list_active()
    return [
        {
            "order_id": d.order_id,
            "customer_id": d.customer_id,
            "status": d.status,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
            "completed_at": d.completed_at,
            "items_count": len(d.items or []),
        }
        for d in rows
    ]


@router.get("/finished", response_model=list[DeliveryListDTO])
def list_finished_deliveries(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("delivery.read")),
):
    facade = DeliveryFacade(db)
    rows = facade.list_finished()
    return [
        {
            "order_id": d.order_id,
            "customer_id": d.customer_id,
            "status": d.status,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
            "completed_at": d.completed_at,
            "items_count": len(d.items or []),
        }
        for d in rows
    ]


@router.get("/{order_id}", response_model=DeliveryDetailDTO)
def get_delivery_detail(
    order_id: str,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("delivery.read")),
):
    facade = DeliveryFacade(db)
    d = facade.get(order_id)
    items = facade.items(order_id)
    return {
        "order_id": d.order_id,
        "customer_id": d.customer_id,
        "status": d.status,
        "remarks": d.remarks,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
        "completed_at": d.completed_at,
        "items": [
            {"product_name": it.product_name, "quantity": it.quantity, "unit_price": it.unit_price}
            for it in items
        ],
    }


@router.get("/{order_id}/items")
def get_cart_items(
    order_id: str,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("delivery.read")),
):
    facade = DeliveryFacade(db)
    items = facade.items(order_id)
    return [
        {"product_name": it.product_name, "quantity": it.quantity, "unit_price": it.unit_price}
        for it in items
    ]


@router.put("/{order_id}/status")
def update_delivery_status(
    order_id: str,
    dto: DeliveryStatusUpdateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("delivery.write")),
):
    facade = DeliveryFacade(db)
    updated = facade.update_status(order_id, dto.status, dto.remark)
    return {"message": "Status updated", "order_id": updated.order_id, "status": updated.status}


@router.get("/{order_id}/logs", response_model=list[DeliveryLogDTO])
def get_delivery_logs(
    order_id: str,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("delivery.read")),
):
    facade = DeliveryFacade(db)
    logs = facade.logs(order_id)
    return logs