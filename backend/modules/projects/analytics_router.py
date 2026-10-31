from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.modules.projects.analytics import PORTFOLIO_KEY
from backend.modules.projects.infrastructure.projections import ProjectSnapshot, ProjectsPortfolioSnapshot

router = APIRouter()

can_read = require_permission("projects.read")


def _with_updated(snap) -> dict:
    data = dict(snap.snapshot or {})
    data["last_updated"] = snap.updated_at.isoformat() if snap.updated_at else None
    return data


@router.get("/overview")
def projects_overview(db: Session = Depends(get_db), user=Depends(can_read)):
    snap = db.get(ProjectsPortfolioSnapshot, PORTFOLIO_KEY)
    if not snap:
        return {
            "projects_total": 0,
            "projects_at_risk": 0,
            "projects_overdue": 0,
            "upcoming_deadlines": [],
            "at_risk": [],
            "generated_at": None,
            "last_updated": None,
        }
    return _with_updated(snap)


@router.get("/projects")
def projects_snapshots(db: Session = Depends(get_db), user=Depends(can_read)):
    """Per-project snapshots (critical path, slack, risk) for the analytics table."""
    rows = db.query(ProjectSnapshot).all()
    return sorted((_with_updated(s) for s in rows), key=lambda s: s.get("deadline") or "")


@router.get("/project/{project_id}")
def project_detail(project_id: int, db: Session = Depends(get_db), user=Depends(can_read)):
    snap = db.get(ProjectSnapshot, project_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not ready or project not found")
    return _with_updated(snap)
