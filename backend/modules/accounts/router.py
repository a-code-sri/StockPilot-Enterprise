from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission

from backend.modules.accounts.application.dtos import (
    TransactionCreateDTO,
    TransactionResponseDTO
)
from backend.modules.accounts.facade import AccountsFacade

router = APIRouter()


@router.post("/", response_model=TransactionResponseDTO)
def create_transaction(
    dto: TransactionCreateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("accounts.write"))
):
    facade = AccountsFacade(db)
    return facade.create_transaction(dto)


@router.get("/", response_model=list[TransactionResponseDTO])
def list_transactions(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("accounts.read"))
):
    facade = AccountsFacade(db)
    return facade.list_transactions()


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("accounts.write"))
):
    facade = AccountsFacade(db)
    facade.delete_transaction(transaction_id)
    return {"message": "Transaction deleted"}


@router.get("/summary")
def get_summary(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("accounts.read"))
):
    facade = AccountsFacade(db)
    return facade.get_summary()