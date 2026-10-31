"""
Outbox handler for the organization snapshot.

Any org change triggers a full rebuild of one snapshot row (cheap: a handful of
aggregate queries). The snapshot also keeps the sorted salary list privately so
the API can build a histogram for any bin count without another scan.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from backend.core.analytics.stats import histogram
from backend.core.time import utcnow
from backend.modules.organization.infrastructure.models import DepartmentModel, EmployeeModel, employee_departments
from backend.modules.organization.infrastructure.projections import OrganizationOverviewSnapshot

logger = logging.getLogger(__name__)

SNAPSHOT_KEY = 0  # single row
DEFAULT_BINS = 10


def _top_executive(db: Session) -> dict | None:
    """
    Head of the organisation: among employees with no manager, the one with the
    most direct reports (ties broken by salary, then seniority).
    """
    reports = aliased(EmployeeModel)
    sub_count = (
        select(func.count(reports.id)).where(reports.manager_id == EmployeeModel.id).correlate(EmployeeModel).scalar_subquery()
    )
    row = (
        db.query(EmployeeModel, sub_count.label("subs"))
        .filter(EmployeeModel.manager_id.is_(None))
        .order_by(sub_count.desc(), EmployeeModel.salary.desc(), EmployeeModel.created_at.asc())
        .first()
    )
    if not row:
        return None
    emp, subs = row
    return {
        "employee_id": emp.employee_id,
        "name": emp.name,
        "job_role": emp.job_role,
        "salary": float(emp.salary),
        "subordinates": int(subs or 0),
        "departments": sorted(d.name for d in emp.departments),
    }


def build_overview_snapshot(db: Session) -> dict[str, Any]:
    count, mn, mx, avg = db.query(
        func.count(EmployeeModel.id), func.min(EmployeeModel.salary), func.max(EmployeeModel.salary),
        func.avg(EmployeeModel.salary),
    ).one()
    median = db.query(func.percentile_cont(0.5).within_group(EmployeeModel.salary)).scalar()

    dept_counts = (
        db.query(DepartmentModel.name, func.count(employee_departments.c.employee_db_id))
        .outerjoin(employee_departments, employee_departments.c.department_id == DepartmentModel.id)
        .group_by(DepartmentModel.name)
        .order_by(func.count(employee_departments.c.employee_db_id).desc(), DepartmentModel.name.asc())
        .all()
    )
    unassigned = (
        db.query(func.count(EmployeeModel.id))
        .filter(~EmployeeModel.id.in_(select(employee_departments.c.employee_db_id)))
        .scalar()
    )

    # An employee can belong to several departments, so shares are of total memberships.
    memberships = sum(int(c) for _, c in dept_counts) + int(unassigned or 0)
    denom = memberships or 1
    share = [{"label": n, "value": int(c), "pct": int(c) / denom * 100.0} for n, c in dept_counts if c]
    if unassigned:
        share.append({"label": "Unassigned", "value": int(unassigned), "pct": int(unassigned) / denom * 100.0})

    salaries = sorted(float(s) for (s,) in db.query(EmployeeModel.salary).all())

    return {
        "department_share": share,
        "salary_stats": {
            "count": int(count or 0),
            "min": float(mn or 0),
            "max": float(mx or 0),
            "avg": float(avg or 0),
            "median": float(median) if median is not None else None,
        },
        "top_executive": _top_executive(db),
        "generated_at": utcnow().isoformat(),
        "_salaries": salaries,
    }


def render_overview(snapshot: dict[str, Any], bins: int) -> dict[str, Any]:
    """Public API shape: drops private fields and adds a histogram for `bins`."""
    data = {k: v for k, v in snapshot.items() if not k.startswith("_")}
    data["salary_histogram"] = {"bins": bins, "series": histogram(snapshot.get("_salaries") or [], bins)}
    return data


def handle_org_changed(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    logger.info("organization: org_changed outbox_id=%s", outbox_id)
    stmt = pg_insert(OrganizationOverviewSnapshot).values(histogram_bins=SNAPSHOT_KEY, snapshot=build_overview_snapshot(db))
    stmt = stmt.on_conflict_do_update(
        index_elements=[OrganizationOverviewSnapshot.histogram_bins],
        set_={"snapshot": stmt.excluded.snapshot, "updated_at": func.now()},
    )
    db.execute(stmt)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("organization analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)
