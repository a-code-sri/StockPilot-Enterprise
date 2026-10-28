from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.analytics.inventory.facade import InventoryAnalyticsFacade

router = APIRouter()


@router.get("/alerts")
def inventory_alerts(
    dead_days: int = 30,
    expiry_days: int = 14,
    consumption_days: int = 14,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read"))
):
    facade = InventoryAnalyticsFacade(db)
    return facade.alerts(dead_days, expiry_days, consumption_days)


@router.get("/reorder-suggestions")
def reorder_suggestions(
    consumption_days: int = 14,
    coverage_days: int = 14,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read"))
):
    facade = InventoryAnalyticsFacade(db)
    return facade.reorder(consumption_days, coverage_days)


@router.get("/stockout-predictions")
def stockout_predictions(
    consumption_days: int = 14,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read"))
):
    facade = InventoryAnalyticsFacade(db)
    return facade.stockout(consumption_days)


@router.get("/series")
def inventory_series(
    consumption_days: int = 30,
    order_months: int = 12,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read"))
):
    facade = InventoryAnalyticsFacade(db)
    return facade.series(consumption_days, order_months)