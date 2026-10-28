from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.accounts.infrastructure.projections import (
    AccountsDailyTotals,
    AccountsDailyCategoryTotals,
)
from backend.modules.analytics.accounts.facade import AccountsAnalyticsFacade
router = APIRouter()


def _d0(x) -> Decimal:
    return x if x is not None else Decimal("0")

@router.get("/overview")
def accounts_analytics_overview(
    days: int = Query(30, ge=1, le=3650),
    top_n: int = Query(5, ge=1, le=50),
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read")),
):
    facade = AccountsAnalyticsFacade(db)
    return facade.overview(days, top_n)


@router.get("/series")
def accounts_series(
    days: int = Query(30, ge=1, le=3650),
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("accounts.read")),
):
    end = date.today()
    start = end - timedelta(days=days - 1)

    rows = (
        db.query(AccountsDailyTotals)
        .filter(AccountsDailyTotals.day >= start, AccountsDailyTotals.day <= end)
        .order_by(AccountsDailyTotals.day.asc())
        .all()
    )

    series = []
    for r in rows:
        income = float(r.income or 0)
        expenses = float(r.expenses or 0)
        series.append(
            {
                "day": r.day.isoformat(),
                "income": income,
                "expenses": expenses,
                "net": income - expenses,
            }
        )

    return {
        "days": days,
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "series": series,
    }