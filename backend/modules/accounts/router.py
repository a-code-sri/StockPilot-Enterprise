from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.pagination import Page, page_params, set_total
from backend.core.rbac.dependencies import require_permission
from backend.modules.accounts.application.dtos import TransactionCreateDTO, TransactionResponseDTO
from backend.modules.accounts.facade import AccountsFacade

router = APIRouter()


@router.post("/", response_model=TransactionResponseDTO, status_code=201)
def create_transaction(
    dto: TransactionCreateDTO,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounts.write")),
):
    return AccountsFacade(db).create_transaction(dto)


@router.get("/", response_model=list[TransactionResponseDTO])
def list_transactions(
    response: Response,
    transaction_type: Optional[Literal["credit", "debit"]] = None,
    category: Optional[str] = None,
    page: Page = Depends(page_params),
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounts.read")),
):
    rows, total = AccountsFacade(db).list_transactions(
        limit=page.limit, offset=page.offset, transaction_type=transaction_type, category=category
    )
    set_total(response, total)
    return rows


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), user=Depends(require_permission("accounts.read"))):
    return AccountsFacade(db).get_summary()


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounts.write")),
):
    if not AccountsFacade(db).delete_transaction(transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted"}
