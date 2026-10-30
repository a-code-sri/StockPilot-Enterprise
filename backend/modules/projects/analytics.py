"""
Outbox handler for project snapshots.

On a change to project P: rebuild P's snapshot (or delete it if P no longer
exists), then rebuild the portfolio from the stored per-project snapshots. This
is O(tasks of P) per event instead of recomputing every project.
"""

import logging
from typing import Any

from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.core.time import utcnow, utctoday
from backend.modules.projects.domain.scheduling import CycleError, TaskInput, compute_schedule
from backend.modules.projects.infrastructure.models import ProjectModel, ProjectTaskModel, project_resources
from backend.modules.projects.infrastructure.projections import ProjectSnapshot, ProjectsPortfolioSnapshot

logger = logging.getLogger(__name__)

PORTFOLIO_KEY = 1
DEFAULT_TOP_N = 10


def to_task_inputs(tasks) -> list[TaskInput]:
    return [
        TaskInput(
            id=t.id,
            name=t.name,
            duration_days=t.duration_days,
            optimistic=t.optimistic,
            most_likely=t.most_likely,
            pessimistic=t.pessimistic,
            predecessor_ids=tuple(p.id for p in (t.predecessors or [])),
            resource_ids=tuple(e.employee_id for e in (t.resources or [])),
        )
        for t in tasks
    ]


def build_project_snapshot(db: Session, proj: ProjectModel) -> dict[str, Any]:
    tasks = db.query(ProjectTaskModel).filter(ProjectTaskModel.project_id == proj.id).all()
    inputs = to_task_inputs(tasks)
    names = {t.id: t.name for t in inputs}

    try:
        sched = compute_schedule(inputs)
        has_cycle = False
    except CycleError:
        sched, has_cycle = None, True

    duration = sched.duration_days if sched else 0.0
    window_days = (proj.deadline - proj.start_date).days
    slack_days = None if has_cycle else window_days - duration

    project_resource_count = (
        db.query(func.count()).select_from(project_resources).filter(project_resources.c.project_id == proj.id).scalar()
    )

    return {
        "project_id": proj.id,
        "title": proj.title,
        "start_date": proj.start_date.isoformat(),
        "deadline": proj.deadline.isoformat(),
        "days_until_deadline": (proj.deadline - utctoday()).days,
        "task_count": len(inputs),
        "critical_path": {
            "duration_days": duration,
            "std_dev_days": sched.std_dev_days if sched else 0.0,
            "task_ids": sched.critical_path if sched else [],
            "task_names": [names[t] for t in sched.critical_path] if sched else [],
            "has_cycle": has_cycle,
        },
        "resources": {
            "project_resource_count": int(project_resource_count or 0),
            "task_resource_count": sum(len(t.resource_ids) for t in inputs),
        },
        "schedule": {
            "window_days": window_days,
            "slack_days": slack_days,
            "at_risk": has_cycle or (slack_days is not None and slack_days < 0),
        },
        "generated_at": utcnow().isoformat(),
    }


def rebuild_project(db: Session, project_id: int) -> None:
    proj = db.get(ProjectModel, project_id)
    if proj is None:
        # Project was deleted: drop its snapshot instead of inserting a row whose
        # foreign key no longer exists (this used to fail and retry forever).
        db.execute(delete(ProjectSnapshot).where(ProjectSnapshot.project_id == project_id))
        return

    stmt = pg_insert(ProjectSnapshot).values(project_id=project_id, snapshot=build_project_snapshot(db, proj))
    stmt = stmt.on_conflict_do_update(
        index_elements=[ProjectSnapshot.project_id],
        set_={"snapshot": stmt.excluded.snapshot, "updated_at": func.now()},
    )
    db.execute(stmt)


def rebuild_portfolio(db: Session, top_n: int = DEFAULT_TOP_N) -> None:
    snaps = [s for (s,) in db.query(ProjectSnapshot.snapshot).all()]
    today = utctoday().isoformat()
    upcoming = sorted(
        (
            {
                "project_id": s["project_id"],
                "title": s["title"],
                "deadline": s["deadline"],
                "slack_days": s["schedule"]["slack_days"],
                "at_risk": s["schedule"]["at_risk"],
                "task_count": s["task_count"],
            }
            for s in snaps
            if s.get("deadline", "") >= today
        ),
        key=lambda x: x["deadline"],
    )[:top_n]

    portfolio = {
        "projects_total": len(snaps),
        "projects_at_risk": sum(1 for s in snaps if s["schedule"]["at_risk"]),
        "projects_overdue": sum(1 for s in snaps if s.get("deadline", today) < today),
        "upcoming_deadlines": upcoming,
        "at_risk": [
            {"project_id": s["project_id"], "title": s["title"], "slack_days": s["schedule"]["slack_days"],
             "deadline": s["deadline"]}
            for s in snaps
            if s["schedule"]["at_risk"]
        ],
        "generated_at": utcnow().isoformat(),
    }

    stmt = pg_insert(ProjectsPortfolioSnapshot).values(id=PORTFOLIO_KEY, snapshot=portfolio)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ProjectsPortfolioSnapshot.id],
        set_={"snapshot": stmt.excluded.snapshot, "updated_at": func.now()},
    )
    db.execute(stmt)


def handle_projects_changed(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    logger.info("projects: projects_changed outbox_id=%s reason=%s", outbox_id, payload.get("reason"))
    project_id = payload.get("project_id")

    if project_id is None:
        ids = [pid for (pid,) in db.query(ProjectModel.id).all()]
        db.execute(delete(ProjectSnapshot).where(ProjectSnapshot.project_id.notin_(ids or [-1])))
        for pid in ids:
            rebuild_project(db, pid)
    else:
        rebuild_project(db, int(project_id))

    rebuild_portfolio(db)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("projects analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)
