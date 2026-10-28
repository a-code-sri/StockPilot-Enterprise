import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.modules.organization.infrastructure.models import (
    EmployeeModel,
    DepartmentModel,
    employee_departments,
)
from backend.modules.organization.infrastructure.projections import OrganizationOverviewSnapshot

logger = logging.getLogger(__name__)


DEFAULT_BINS = 10


def _to_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def _compute_histogram(salaries: list[float], bins: int) -> list[dict[str, float]]:
    if bins <= 0:
        bins = DEFAULT_BINS

    if not salaries:
        return []

    mn = min(salaries)
    mx = max(salaries)

    # All same salary -> one bucket
    if mx <= mn:
        return [{"bin_start": mn, "bin_end": mx, "count": float(len(salaries))}]

    width = (mx - mn) / bins
    # avoid zero width due to float rounding
    if width <= 0:
        width = 1.0

    counts = [0] * bins
    for s in salaries:
        idx = int((s - mn) / width)
        if idx >= bins:
            idx = bins - 1
        if idx < 0:
            idx = 0
        counts[idx] += 1

    out = []
    for i, c in enumerate(counts):
        b0 = mn + i * width
        b1 = mn + (i + 1) * width
        out.append({"bin_start": b0, "bin_end": b1, "count": float(c)})
    return out


def _build_overview_snapshot(db: Session, histogram_bins: int) -> dict[str, Any]:
    # ---- Salary stats ----
    # count, min, max, avg
    total_employees, min_sal, max_sal, avg_sal = db.query(
        func.count(EmployeeModel.id),
        func.coalesce(func.min(EmployeeModel.salary), 0),
        func.coalesce(func.max(EmployeeModel.salary), 0),
        func.coalesce(func.avg(EmployeeModel.salary), 0),
    ).one()

    # median (Postgres)
    median_sal = None
    try:
        median_sal = db.query(
            func.percentile_cont(0.5).within_group(EmployeeModel.salary)
        ).scalar()
    except Exception:
        median_sal = None

    # ---- Top executive (highest salary) ----
    top_emp = (
        db.query(EmployeeModel)
        .order_by(EmployeeModel.salary.desc(), EmployeeModel.id.asc())
        .first()
    )
    top_exec = None
    if top_emp:
        subordinate_count = (
            db.query(func.count(EmployeeModel.id))
            .filter(EmployeeModel.manager_id == top_emp.id)
            .scalar()
            or 0
        )
        top_exec = {
            "employee_id": top_emp.employee_id,
            "name": top_emp.name,
            "job_role": top_emp.job_role,
            "salary": _to_float(top_emp.salary),
            "subordinates": int(subordinate_count),
        }

    # ---- Department share (headcount per department) ----
    # count of employees in each department (based on association table)
    dept_counts = (
        db.query(
            DepartmentModel.name,
            func.count(employee_departments.c.employee_db_id).label("headcount"),
        )
        .select_from(DepartmentModel)
        .join(employee_departments, employee_departments.c.department_id == DepartmentModel.id, isouter=True)
        .group_by(DepartmentModel.name)
        .order_by(func.count(employee_departments.c.employee_db_id).desc(), DepartmentModel.name.asc())
        .all()
    )

    # employees with no department -> "Unassigned"
    # count employees not in association table
    unassigned_count = (
        db.query(func.count(EmployeeModel.id))
        .filter(
            ~EmployeeModel.id.in_(
                select(employee_departments.c.employee_db_id)
            )
        )
        .scalar()
        or 0
    )

    dept_share = []
    denom = int(total_employees or 0) if int(total_employees or 0) > 0 else 1

    for name, headcount in dept_counts:
        hc = int(headcount or 0)
        if hc == 0:
            continue
        dept_share.append({"label": name, "value": hc, "pct": (hc / denom) * 100.0})

    if unassigned_count:
        dept_share.append({"label": "Unassigned", "value": int(unassigned_count), "pct": (int(unassigned_count) / denom) * 100.0})

    # ---- Histogram ----
    salaries = [float(x[0]) for x in db.query(EmployeeModel.salary).all()]
    histogram = _compute_histogram(salaries, histogram_bins)

    return {
        "department_share": dept_share,
        "salary_stats": {
            "count": int(total_employees or 0),
            "min": _to_float(min_sal),
            "max": _to_float(max_sal),
            "avg": _to_float(avg_sal),
            "median": _to_float(median_sal) if median_sal is not None else None,
        },
        "salary_histogram": {
            "bins": int(histogram_bins),
            "series": histogram,
        },
        "top_executive": top_exec,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def handle_org_changed(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    bins = payload.get("histogram_bins")
    try:
        bins = int(bins) if bins is not None else DEFAULT_BINS
    except Exception:
        bins = DEFAULT_BINS

    logger.info("organization analytics: org_changed outbox_id=%s bins=%s", outbox_id, bins)

    snapshot = _build_overview_snapshot(db, bins)

    stmt = pg_insert(OrganizationOverviewSnapshot).values(
        histogram_bins=bins,
        snapshot=snapshot,
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=[OrganizationOverviewSnapshot.histogram_bins],
        set_={
            "snapshot": stmt.excluded.snapshot,
            "updated_at": func.now(),
        },
    )

    db.execute(stmt)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("organization analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)