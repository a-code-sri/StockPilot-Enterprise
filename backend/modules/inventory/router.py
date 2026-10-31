from contextlib import contextmanager
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.pagination import Page, page_params, set_total
from backend.core.rbac.dependencies import require_permission
from backend.modules.inventory.application.dtos import (
    InventoryCreateDTO,
    InventoryLogDTO,
    InventoryResponseDTO,
    InventoryStatusUpdateDTO,
    InventoryUpdateDTO,
)
from backend.modules.inventory.application.services import InventoryConflict, InventoryError, InventoryNotFound
from backend.modules.inventory.facade import InventoryFacade

router = APIRouter()

can_read = require_permission("inventory.read")
can_write = require_permission("inventory.write")


@contextmanager
def _http_errors():
    try:
        yield
    except InventoryNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InventoryConflict as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InventoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=InventoryResponseDTO, status_code=201)
def create_inventory(dto: InventoryCreateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    with _http_errors():
        return InventoryFacade(db).create_inventory(dto)


@router.get("/", response_model=list[InventoryResponseDTO])
def list_inventory(
    response: Response,
    status: Optional[Literal["under_use", "ordered", "consumed"]] = None,
    search: Optional[str] = None,
    page: Page = Depends(page_params),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    rows, total = InventoryFacade(db).list_inventory(
        status=status, search=search, limit=page.limit, offset=page.offset
    )
    set_total(response, total)
    return rows


@router.get("/{item_id}", response_model=InventoryResponseDTO)
def get_inventory(item_id: int, db: Session = Depends(get_db), user=Depends(can_read)):
    with _http_errors():
        return InventoryFacade(db).get_item(item_id)


@router.put("/{item_id}", response_model=InventoryResponseDTO)
def move_stock(item_id: int, dto: InventoryUpdateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    """Record a stock movement: add, consume, deliver, order or return."""
    with _http_errors():
        return InventoryFacade(db).update_inventory(item_id, dto)


@router.put("/{item_id}/status", response_model=InventoryResponseDTO)
def update_inventory_status(
    item_id: int, dto: InventoryStatusUpdateDTO, db: Session = Depends(get_db), user=Depends(can_write)
):
    with _http_errors():
        return InventoryFacade(db).update_status(item_id, dto.status)


@router.delete("/{item_id}")
def delete_inventory(item_id: int, db: Session = Depends(get_db), user=Depends(can_write)):
    with _http_errors():
        InventoryFacade(db).delete_inventory(item_id)
    return {"message": "Inventory deleted"}


@router.get("/{item_id}/logs", response_model=list[InventoryLogDTO])
def get_logs(item_id: int, db: Session = Depends(get_db), user=Depends(can_read)):
    with _http_errors():
        return InventoryFacade(db).get_inventory_logs(item_id)
