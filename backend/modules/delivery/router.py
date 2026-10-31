from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.pagination import Page, page_params, set_total
from backend.core.rbac.dependencies import require_permission
from backend.modules.delivery.application.dtos import (
    DeliveryCreateDTO,
    DeliveryDetailDTO,
    DeliveryItemDTO,
    DeliveryListDTO,
    DeliveryLogDTO,
    DeliveryStatusUpdateDTO,
)
from backend.modules.delivery.domain.entities import allowed_next
from backend.modules.delivery.facade import DeliveryFacade

router = APIRouter()

can_read = require_permission("delivery.read")
can_write = require_permission("delivery.write")


def _status(d) -> str:
    return getattr(d.status, "value", d.status)


def _list_row(d) -> dict:
    return {
        "order_id": d.order_id,
        "customer_id": d.customer_id,
        "status": _status(d),
        "created_at": d.created_at,
        "updated_at": d.updated_at,
        "completed_at": d.completed_at,
        "items_count": len(d.items or []),
        "allowed_next": allowed_next(_status(d)),
    }


def _item_row(it) -> dict:
    return {
        "product_name": it.product_name,
        "quantity": it.quantity,
        "unit_price": float(it.unit_price),
        "inventory_item_id": it.inventory_item_id,
    }


@router.post("/", status_code=201)
def create_delivery(dto: DeliveryCreateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    delivery = DeliveryFacade(db).create(dto)
    return {"message": "Delivery created", "order_id": delivery.order_id}


@router.get("/active", response_model=list[DeliveryListDTO])
def list_active_deliveries(
    response: Response, page: Page = Depends(page_params), db: Session = Depends(get_db), user=Depends(can_read)
):
    rows, total = DeliveryFacade(db).list_active(limit=page.limit, offset=page.offset)
    set_total(response, total)
    return [_list_row(d) for d in rows]


@router.get("/finished", response_model=list[DeliveryListDTO])
def list_finished_deliveries(
    response: Response, page: Page = Depends(page_params), db: Session = Depends(get_db), user=Depends(can_read)
):
    rows, total = DeliveryFacade(db).list_finished(limit=page.limit, offset=page.offset)
    set_total(response, total)
    return [_list_row(d) for d in rows]


@router.get("/{order_id}", response_model=DeliveryDetailDTO)
def get_delivery_detail(order_id: str, db: Session = Depends(get_db), user=Depends(can_read)):
    facade = DeliveryFacade(db)
    d = facade.get(order_id)
    return {
        "order_id": d.order_id,
        "customer_id": d.customer_id,
        "status": _status(d),
        "remarks": d.remarks,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
        "completed_at": d.completed_at,
        "stock_deducted": d.stock_deducted,
        "allowed_next": allowed_next(_status(d)),
        "items": [_item_row(it) for it in facade.items(order_id)],
    }


@router.get("/{order_id}/items", response_model=list[DeliveryItemDTO])
def get_cart_items(order_id: str, db: Session = Depends(get_db), user=Depends(can_read)):
    return [_item_row(it) for it in DeliveryFacade(db).items(order_id)]


@router.put("/{order_id}/status")
def update_delivery_status(
    order_id: str, dto: DeliveryStatusUpdateDTO, db: Session = Depends(get_db), user=Depends(can_write)
):
    updated = DeliveryFacade(db).update_status(order_id, dto.status, dto.remark)
    return {
        "message": "Status updated",
        "order_id": updated.order_id,
        "status": _status(updated),
        "allowed_next": allowed_next(_status(updated)),
    }


@router.get("/{order_id}/logs", response_model=list[DeliveryLogDTO])
def get_delivery_logs(order_id: str, db: Session = Depends(get_db), user=Depends(can_read)):
    return DeliveryFacade(db).logs(order_id)
