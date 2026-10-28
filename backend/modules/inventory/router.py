from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission

from backend.modules.inventory.application.dtos import (
    InventoryCreateDTO,
    InventoryUpdateDTO,
    InventoryStatusUpdateDTO,
    InventoryResponseDTO,
    InventoryLogDTO,
)
from backend.modules.inventory.facade import InventoryFacade

router = APIRouter()


@router.post("/", response_model=InventoryResponseDTO)
def create_inventory(
    dto: InventoryCreateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.write"))
):
    facade = InventoryFacade(db)
    return facade.create_inventory(dto)


@router.get("/", response_model=list[InventoryResponseDTO])
def list_inventory(
    status: str = None,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.read"))
):
    facade = InventoryFacade(db)
    return facade.list_inventory(status)


@router.put("/{name}", response_model=InventoryResponseDTO)
def update_inventory(
    name: str,
    dto: InventoryUpdateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.write"))
):
    facade = InventoryFacade(db)
    try:
        return facade.update_inventory(name, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{name}/status", response_model=InventoryResponseDTO)
def update_inventory_status(
    name: str,
    dto: InventoryStatusUpdateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.write"))
):
    facade = InventoryFacade(db)
    try:
        return facade.update_status(name, dto.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
def delete_inventory(
    name: str,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.write"))
):
    facade = InventoryFacade(db)
    facade.delete_inventory(name)
    return {"message": "Inventory deleted"}


@router.get("/{name}/logs", response_model=list[InventoryLogDTO])
def get_logs(
    name: str,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("inventory.read"))
):
    facade = InventoryFacade(db)
    return facade.get_inventory_logs(name)