from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.organization.infrastructure.projections import OrganizationOverviewSnapshot

router = APIRouter()


@router.get("/overview")
def organization_overview(
    histogram_bins: int = Query(10, ge=1, le=100),
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("organization")),
):
    snap = db.get(OrganizationOverviewSnapshot, histogram_bins)
    if not snap:
        # If worker hasn't produced a snapshot yet, return a safe empty structure.
        # (You can optionally compute live here, but that would defeat the projection idea.)
        return {
            "department_share": [],
            "salary_stats": {"count": 0, "min": 0, "max": 0, "avg": 0, "median": None},
            "salary_histogram": {"bins": histogram_bins, "series": []},
            "top_executive": None,
            "generated_at": None,
            "last_updated": None,
        }

    # snapshot is already JSON-serializable (JSONB)
    data = dict(snap.snapshot or {})
    data["last_updated"] = snap.updated_at.isoformat() if snap.updated_at else None
    return data