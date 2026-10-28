from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.analytics.organization.facade import OrganizationAnalyticsFacade

router = APIRouter()


@router.get("/overview")
def organization_overview(
    histogram_bins: int = 10,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("analytics.read")),
):
    facade = OrganizationAnalyticsFacade(db)
    return facade.overview(histogram_bins=histogram_bins)