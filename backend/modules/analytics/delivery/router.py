from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.analytics.delivery.facade import DeliveryAnalyticsFacade

router = APIRouter()


@router.get("/overview")
def delivery_analytics_overview(
    days_month: int = 30,
    days_year: int = 365,
    top_n: int = 10,
    ma_window_month: int = 7,
    ma_window_year: int = 30,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read")),
):
    facade = DeliveryAnalyticsFacade(db)
    return facade.overview(days_month, days_year, top_n, ma_window_month, ma_window_year)