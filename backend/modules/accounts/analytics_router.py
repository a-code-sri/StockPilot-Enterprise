from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.modules.accounts.application.analytics_service import AccountsAnalyticsService

router = APIRouter()

can_read = require_permission("accounts.read")


@router.get("/overview")
def accounts_analytics_overview(
    days: int = Query(30, ge=1, le=3650),
    top_n: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    return AccountsAnalyticsService(db).overview(days, top_n)


@router.get("/series")
def accounts_series(days: int = Query(30, ge=1, le=3650), db: Session = Depends(get_db), user=Depends(can_read)):
    return AccountsAnalyticsService(db).series(days)


@router.get("/anomalies")
def accounts_anomalies(
    days: int = Query(180, ge=7, le=3650),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    """Transactions whose amount is a statistical outlier for their type/category."""
    return AccountsAnalyticsService(db).anomalies(days, limit)
