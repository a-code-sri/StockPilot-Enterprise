from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.analytics.accounts.facade import AccountsAnalyticsFacade

router = APIRouter()


@router.get("/overview")
def accounts_analytics_overview(
    days: int = 30,
    top_n: int = 5,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read")),
):
    facade = AccountsAnalyticsFacade(db)
    return facade.overview(days, top_n)