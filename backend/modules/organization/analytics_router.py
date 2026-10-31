from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.modules.organization.analytics import SNAPSHOT_KEY, render_overview
from backend.modules.organization.infrastructure.projections import OrganizationOverviewSnapshot

router = APIRouter()


@router.get("/overview")
def organization_overview(
    histogram_bins: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_permission("organization.read")),
):
    snap = db.get(OrganizationOverviewSnapshot, SNAPSHOT_KEY)
    if not snap:
        # Worker hasn't produced a snapshot yet (fresh install with no org changes).
        return {
            "department_share": [],
            "salary_stats": {"count": 0, "min": 0, "max": 0, "avg": 0, "median": None},
            "salary_histogram": {"bins": histogram_bins, "series": []},
            "top_executive": None,
            "generated_at": None,
            "last_updated": None,
        }

    data = render_overview(snap.snapshot or {}, histogram_bins)
    data["last_updated"] = snap.updated_at.isoformat() if snap.updated_at else None
    return data
