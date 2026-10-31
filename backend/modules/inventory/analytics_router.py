from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.modules.inventory.application.analytics_service import InventoryAnalyticsService

router = APIRouter()

can_read = require_permission("inventory.read")


@router.get("/series")
def inventory_series(
    consumption_days: int = Query(14, ge=1, le=3650),
    order_months: int = Query(6, ge=1, le=120),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    return InventoryAnalyticsService(db).series(consumption_days, order_months)


@router.get("/alerts")
def inventory_alerts(
    dead_days: int = Query(30, ge=1, le=3650),
    expiry_days: int = Query(14, ge=1, le=3650),
    consumption_days: int = Query(14, ge=1, le=3650),
    coverage_days: int = Query(14, ge=1, le=365),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    return InventoryAnalyticsService(db).alerts(dead_days, expiry_days, consumption_days, coverage_days)


@router.get("/reorder-suggestions")
def reorder_suggestions(
    consumption_days: int = Query(14, ge=1, le=3650),
    coverage_days: int = Query(14, ge=1, le=365),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    return InventoryAnalyticsService(db).reorder_suggestions(consumption_days, coverage_days)


@router.get("/stockout-predictions")
def stockout_predictions(
    consumption_days: int = Query(14, ge=1, le=3650),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    return InventoryAnalyticsService(db).stockout_predictions(consumption_days)


@router.get("/anomalies")
def inventory_anomalies(
    days: int = Query(60, ge=7, le=365),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    """Item-days with unusually high consumption compared with that item's own history."""
    return InventoryAnalyticsService(db).anomalies(days, limit)
