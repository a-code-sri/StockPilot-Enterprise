import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.modules.projects.infrastructure.models import (
    ProjectModel,
    ProjectTaskModel,
    task_predecessors,
    project_resources,
    task_resources,
)
from backend.modules.projects.infrastructure.projections import (
    ProjectSnapshot,
    ProjectsPortfolioSnapshot,
)

logger = logging.getLogger(__name__)


@dataclass
class TaskNode:
    id: int
    name: str
    duration: float  # expected duration in days


def _task_expected_duration(t: ProjectTaskModel) -> float:
    """
    If PERT estimates exist, use expected duration:
      (o + 4m + p) / 6
    else fallback to duration_days.
    """
    if t.optimistic is not None and t.most_likely is not None and t.pessimistic is not None:
        try:
            return float((t.optimistic + 4 * t.most_likely + t.pessimistic) / 6.0)
        except Exception:
            pass
    return float(t.duration_days or 0.0)


def _compute_longest_path(tasks: dict[int, TaskNode], preds: dict[int, list[int]]) -> dict[str, Any]:
    """
    Longest path in DAG (critical path length), using Kahn topo sort + DP.
    Returns duration + critical path node ids.
    If cycles exist, returns best-effort with a flag.
    """
    # Build in-degree and successors
    indeg = {tid: 0 for tid in tasks}
    succ: dict[int, list[int]] = {tid: [] for tid in tasks}

    for t, p_list in preds.items():
        for p in p_list:
            if t in indeg and p in indeg:
                indeg[t] += 1
                succ[p].append(t)

    # Kahn queue
    q = [tid for tid, d in indeg.items() if d == 0]
    topo = []
    while q:
        n = q.pop()
        topo.append(n)
        for s in succ.get(n, []):
            indeg[s] -= 1
            if indeg[s] == 0:
                q.append(s)

    has_cycle = len(topo) != len(tasks)

    # DP: longest finish time
    dp: dict[int, float] = {tid: tasks[tid].duration for tid in tasks}
    parent: dict[int, int | None] = {tid: None for tid in tasks}

    # if cycle, topo is partial; still iterate it and then all nodes as fallback
    iter_nodes = topo + [tid for tid in tasks if tid not in topo]

    for tid in iter_nodes:
        best_pred = None
        best_val = 0.0
        for p in preds.get(tid, []):
            if p in dp and dp[p] > best_val:
                best_val = dp[p]
                best_pred = p
        dp[tid] = tasks[tid].duration + best_val
        parent[tid] = best_pred

    end_task = max(dp, key=lambda k: dp[k]) if dp else None
    crit_duration = dp[end_task] if end_task is not None else 0.0

    # Backtrack critical path ids
    crit_path = []
    cur = end_task
    seen = set()
    while cur is not None and cur in parent and cur not in seen:
        seen.add(cur)
        crit_path.append(cur)
        cur = parent[cur]
    crit_path.reverse()

    return {
        "critical_path_duration_days": float(crit_duration),
        "critical_path_task_ids": crit_path,
        "has_cycle": has_cycle,
    }


def _build_project_snapshot(db: Session, project_id: int) -> dict[str, Any]:
    proj = db.get(ProjectModel, project_id)
    if not proj:
        return {"project_id": project_id, "error": "project_not_found"}

    tasks_rows = (
        db.query(ProjectTaskModel)
        .filter(ProjectTaskModel.project_id == project_id)
        .all()
    )

    tasks: dict[int, TaskNode] = {}
    for t in tasks_rows:
        tasks[t.id] = TaskNode(
            id=t.id,
            name=t.name,
            duration=_task_expected_duration(t),
        )

    # predecessor edges: (task_id, predecessor_id)
    pred_rows = db.execute(
        select(task_predecessors.c.task_id, task_predecessors.c.predecessor_id)
        .where(task_predecessors.c.task_id.in_(list(tasks.keys())) if tasks else False)
    ).all()

    preds: dict[int, list[int]] = {tid: [] for tid in tasks}
    for task_id, pred_id in pred_rows:
        if task_id in preds:
            preds[task_id].append(pred_id)

    cpm = _compute_longest_path(tasks, preds)

    # resource counts
    project_resource_count = db.execute(
        select(func.count())
        .select_from(project_resources)
        .where(project_resources.c.project_id == project_id)
    ).scalar() or 0

    task_resource_count = db.execute(
        select(func.count())
        .select_from(task_resources)
        .where(task_resources.c.task_id.in_(list(tasks.keys())) if tasks else False)
    ).scalar() or 0

    # slack vs project calendar window
    start = proj.start_date
    deadline = proj.deadline
    window_days = (deadline - start).days if start and deadline else None
    crit = float(cpm["critical_path_duration_days"] or 0.0)
    slack_days = None
    if window_days is not None:
        slack_days = float(window_days) - crit

    return {
        "project_id": proj.id,
        "title": proj.title,
        "start_date": proj.start_date.isoformat(),
        "deadline": proj.deadline.isoformat(),
        "task_count": len(tasks),
        "critical_path": {
            "duration_days": crit,
            "task_ids": cpm["critical_path_task_ids"],
            "task_names": [tasks[tid].name for tid in cpm["critical_path_task_ids"] if tid in tasks],
            "has_cycle": bool(cpm["has_cycle"]),
        },
        "resources": {
            "project_resource_count": int(project_resource_count),
            "task_resource_count": int(task_resource_count),
        },
        "schedule": {
            "window_days": window_days,
            "slack_days": slack_days,
            "at_risk": (slack_days is not None and slack_days < 0),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_portfolio_snapshot(db: Session, *, top_n: int = 10) -> dict[str, Any]:
    projects = db.query(ProjectModel).order_by(ProjectModel.deadline.asc()).all()

    per_project = []
    at_risk = 0
    for p in projects:
        snap = _build_project_snapshot(db, p.id)
        per_project.append(snap)
        if snap.get("schedule", {}).get("at_risk"):
            at_risk += 1

    # upcoming deadlines
    upcoming = sorted(
        [
            {
                "project_id": s.get("project_id"),
                "title": s.get("title"),
                "deadline": s.get("deadline"),
                "slack_days": s.get("schedule", {}).get("slack_days"),
                "task_count": s.get("task_count"),
            }
            for s in per_project
            if s.get("project_id") is not None
        ],
        key=lambda x: x["deadline"] or "",
    )[:top_n]

    return {
        "projects_total": len(projects),
        "projects_at_risk": int(at_risk),
        "upcoming_deadlines": upcoming,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def handle_projects_changed(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    """
    Rebuild snapshots when projects/tasks change.
    payload may include:
      - project_id (optional)
      - top_n (optional for portfolio)
    """
    logger.info("projects analytics: projects_changed outbox_id=%s payload=%s", outbox_id, payload)

    project_id = payload.get("project_id")
    top_n = payload.get("top_n")
    try:
        top_n = int(top_n) if top_n is not None else 10
    except Exception:
        top_n = 10

    # Rebuild either one project snapshot or all
    if project_id is not None:
        try:
            pid = int(project_id)
        except Exception:
            pid = None

        if pid is not None:
            snap = _build_project_snapshot(db, pid)
            stmt = pg_insert(ProjectSnapshot).values(
                project_id=pid,
                snapshot=snap,
            ).on_conflict_do_update(
                index_elements=[ProjectSnapshot.project_id],
                set_={"snapshot": pg_insert(ProjectSnapshot).excluded.snapshot, "updated_at": func.now()},
            )
            db.execute(stmt)

    else:
        # rebuild all projects
        ids = [x[0] for x in db.query(ProjectModel.id).all()]
        for pid in ids:
            snap = _build_project_snapshot(db, pid)
            stmt = pg_insert(ProjectSnapshot).values(
                project_id=pid,
                snapshot=snap,
            ).on_conflict_do_update(
                index_elements=[ProjectSnapshot.project_id],
                set_={"snapshot": pg_insert(ProjectSnapshot).excluded.snapshot, "updated_at": func.now()},
            )
            db.execute(stmt)

    # Always rebuild portfolio snapshot too
    portfolio = _build_portfolio_snapshot(db, top_n=top_n)
    stmtp = pg_insert(ProjectsPortfolioSnapshot).values(
        id=1,
        snapshot=portfolio,
    ).on_conflict_do_update(
        index_elements=[ProjectsPortfolioSnapshot.id],
        set_={"snapshot": pg_insert(ProjectsPortfolioSnapshot).excluded.snapshot, "updated_at": func.now()},
    )
    db.execute(stmtp)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("projects analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)