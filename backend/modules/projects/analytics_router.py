from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.projects.infrastructure.projections import (
    ProjectsPortfolioSnapshot,
    ProjectSnapshot,
)

router = APIRouter()


@router.get("/overview")
def projects_overview(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.read")),
):
    snap = db.get(ProjectsPortfolioSnapshot, 1)
    if not snap:
        return {
            "projects_total": 0,
            "projects_at_risk": 0,
            "upcoming_deadlines": [],
            "generated_at": None,
            "last_updated": None,
        }

    data = dict(snap.snapshot or {})
    data["last_updated"] = snap.updated_at.isoformat() if snap.updated_at else None
    return data


@router.get("/project/{project_id}")
def project_detail(
    project_id: int,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.read")),
):
    snap = db.get(ProjectSnapshot, project_id)
    if not snap:
        return {
            "project_id": project_id,
            "error": "snapshot_not_ready",
            "last_updated": None,
        }

    data = dict(snap.snapshot or {})
    data["last_updated"] = snap.updated_at.isoformat() if snap.updated_at else None
    return data