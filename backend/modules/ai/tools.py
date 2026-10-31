"""
Read-only "tools" the assistant can call. Each tool declares the permission it
needs; the assistant only ever sees tools the current user is allowed to use, so
the AI cannot reveal data the user could not open in the app.

Outputs are deliberately compact (top-N lists, rounded numbers) because small
local models have limited context windows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.core.time import utctoday


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    permission: str | None
    parameters: dict[str, Any]
    run: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.parameters},
        }


def _params(**props: dict) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": []}


def _int(v, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


# ---------------- inventory ----------------

def _inventory_alerts(db: Session, **_):
    from backend.modules.inventory.application.analytics_service import InventoryAnalyticsService

    a = InventoryAnalyticsService(db).alerts(dead_days=30, expiry_days=14, consumption_days=14)
    return {
        "counts": {k: a[k] for k in ("exhausted_count", "dead_stock_count", "near_expiry_count", "reorder_count")},
        "exhausted": [i["name"] for i in a["exhausted"][:10]],
        "near_expiry": a["near_expiry"][:10],
        "dead_stock": a["dead_stock"][:10],
        "reorder": a["reorder"][:10],
    }


def _stockout(db: Session, limit=10, **_):
    from backend.modules.inventory.application.analytics_service import InventoryAnalyticsService

    rows = InventoryAnalyticsService(db).stockout_predictions(14)
    return [r for r in rows if r["days_to_stockout"] is not None][: _int(limit, 10, 1, 30)]


def _reorder(db: Session, limit=10, **_):
    from backend.modules.inventory.application.analytics_service import InventoryAnalyticsService

    rows = InventoryAnalyticsService(db).reorder_suggestions(14, 14)
    return [r for r in rows if r["suggested_reorder_quantity"] > 0][: _int(limit, 10, 1, 30)]


def _search_inventory(db: Session, query: str = "", **_):
    from backend.modules.inventory.infrastructure.repository import SQLAlchemyInventoryRepository

    rows, total = SQLAlchemyInventoryRepository(db).list_items(search=str(query or ""), limit=15, offset=0)
    return {
        "total_matches": total,
        "items": [
            {"id": r.id, "name": r.name, "quantity": r.quantity, "on_order": r.on_order_quantity,
             "status": r.status.value, "price": float(r.price),
             "expiry_date": r.expiry_date.isoformat() if r.expiry_date else None}
            for r in rows
        ],
    }


def _inventory_anomalies(db: Session, **_):
    from backend.modules.inventory.application.analytics_service import InventoryAnalyticsService

    return InventoryAnalyticsService(db).anomalies(days=60, limit=10)


# ---------------- accounts ----------------

def _accounts_summary(db: Session, days=30, **_):
    from backend.modules.accounts.application.analytics_service import AccountsAnalyticsService

    d = _int(days, 30, 1, 3650)
    o = AccountsAnalyticsService(db).overview(d, 5)
    return {
        "window_days": d,
        "income_vs_expenses": o["income_vs_expenses"],
        "top_expense_categories": o["expense_by_category"][:5],
        "top_income_categories": o["income_by_category"][:5],
        "rankings": o["rankings"],
        "liquidity_30d": o["liquidity"]["score_30d"],
    }


def _transaction_anomalies(db: Session, days=180, **_):
    from backend.modules.accounts.application.analytics_service import AccountsAnalyticsService

    return AccountsAnalyticsService(db).anomalies(_int(days, 180, 7, 3650), 10)


# ---------------- delivery ----------------

def _delivery_overview(db: Session, days=30, **_):
    from backend.modules.delivery.analytics_router import build_period

    d = _int(days, 30, 1, 3650)
    p = build_period(db, d, 7, 5, 0)
    series = p["moving_average"]["series"]
    return {
        "window_days": d,
        "delivered_total": sum(x["count"] for x in series),
        "status_of_orders_created_in_window": p["status_distribution"]["series"],
        "most_ordered_items": p["most_ordered_items"]["series"],
    }


def _active_deliveries(db: Session, limit=20, **_):
    from backend.modules.delivery.facade import DeliveryFacade

    rows, total = DeliveryFacade(db).list_active(limit=_int(limit, 20, 1, 50), offset=0)
    today = utctoday()
    return {
        "total_active": total,
        "deliveries": [
            {"order_id": d.order_id, "customer_id": d.customer_id, "status": d.status.value,
             "age_days": (today - d.created_at.date()).days, "items": len(d.items)}
            for d in rows
        ],
    }


# ---------------- organization ----------------

def _org_overview(db: Session, **_):
    from backend.modules.organization.analytics import SNAPSHOT_KEY
    from backend.modules.organization.infrastructure.projections import OrganizationOverviewSnapshot

    snap = db.get(OrganizationOverviewSnapshot, SNAPSHOT_KEY)
    if not snap:
        return {"note": "No organization data yet."}
    s = snap.snapshot
    return {k: s.get(k) for k in ("department_share", "salary_stats", "top_executive")}


def _search_employees(db: Session, query: str = "", department: str = "", **_):
    from backend.modules.organization.infrastructure.repository import SQLAlchemyOrganizationRepository

    rows, total = SQLAlchemyOrganizationRepository(db).search_employees(
        q=str(query or "") or None, department=str(department or "") or None, manager_employee_id=None,
        limit=15, offset=0,
    )
    return {
        "total_matches": total,
        "employees": [
            {"employee_id": e.employee_id, "name": e.name, "job_role": e.job_role,
             "departments": [d.name for d in e.departments],
             "manager": e.manager.employee_id if e.manager else None}
            for e in rows
        ],
    }


# ---------------- projects ----------------

def _projects_overview(db: Session, **_):
    from backend.modules.projects.analytics import PORTFOLIO_KEY
    from backend.modules.projects.infrastructure.projections import ProjectsPortfolioSnapshot

    snap = db.get(ProjectsPortfolioSnapshot, PORTFOLIO_KEY)
    return snap.snapshot if snap else {"note": "No projects yet."}


def _project_schedule(db: Session, project_id=None, **_):
    from fastapi import HTTPException

    from backend.modules.projects.facade import ProjectsFacade

    try:
        sim = ProjectsFacade(db).simulate(int(project_id))
    except (TypeError, ValueError):
        return {"error": "project_id must be an integer"}
    except HTTPException as e:
        return {"error": e.detail}
    names = {t["id"]: t["name"] for t in sim["tasks"]}
    return {
        "project_id": sim["project_id"],
        "duration_days": round(sim["project_duration_days"], 2),
        "days_to_spare_before_deadline": round(sim["deadline_days_remaining"], 2),
        "critical_path": [names.get(t, t) for t in sim["critical_path_task_ids"]],
        "resource_conflicts": {emp: len(c) for emp, c in sim["resource_conflicts"].items()},
    }


# ---------------- business ----------------

def _business_profile(db: Session, **_):
    from backend.modules.business.application.services import BusinessService

    svc = BusinessService(db)
    p = svc.to_dict(svc.get())
    return {k: p.get(k) for k in ("configured", "legal_name", "trade_name", "gstin", "state", "verification_status")}


TOOLS: tuple[Tool, ...] = (
    Tool("inventory_alerts", "Inventory health: out-of-stock, near-expiry, dead stock and items needing reorder.",
         "inventory.read", _params(), _inventory_alerts),
    Tool("stockout_predictions", "Items predicted to run out soonest, based on recent consumption.",
         "inventory.read", _params(limit={"type": "integer", "description": "max items"}), _stockout),
    Tool("reorder_suggestions", "How many units to reorder per item to cover the next 14 days.",
         "inventory.read", _params(limit={"type": "integer"}), _reorder),
    Tool("search_inventory", "Find inventory items by name; returns quantity, status, price, expiry.",
         "inventory.read", _params(query={"type": "string"}), _search_inventory),
    Tool("inventory_anomalies", "Days with unusually high consumption of an item.",
         "inventory.read", _params(), _inventory_anomalies),
    Tool("accounts_summary", "Income, expenses, net, top categories, counterparties and liquidity score.",
         "accounts.read", _params(days={"type": "integer", "description": "look-back window in days"}),
         _accounts_summary),
    Tool("transaction_anomalies", "Transactions with unusually large amounts for their category.",
         "accounts.read", _params(days={"type": "integer"}), _transaction_anomalies),
    Tool("delivery_overview", "Deliveries completed, order status breakdown and most ordered items.",
         "delivery.read", _params(days={"type": "integer"}), _delivery_overview),
    Tool("active_deliveries", "Open deliveries with their status and age in days.",
         "delivery.read", _params(limit={"type": "integer"}), _active_deliveries),
    Tool("organization_overview", "Headcount by department, salary statistics and head of organisation.",
         "organization.read", _params(), _org_overview),
    Tool("search_employees", "Find employees by name/id/role and/or department.",
         "organization.read", _params(query={"type": "string"}, department={"type": "string"}), _search_employees),
    Tool("projects_overview", "Portfolio: totals, projects at risk of missing deadlines, upcoming deadlines.",
         "projects.read", _params(), _projects_overview),
    Tool("project_schedule", "Critical path, expected duration and slack for one project (needs project_id).",
         "projects.read", _params(project_id={"type": "integer"}), _project_schedule),
    Tool("business_profile", "The company's legal name, GSTIN and registration verification status.",
         None, _params(), _business_profile),
)

TOOLS_BY_NAME = {t.name: t for t in TOOLS}

# Data gathered for "Summarize" buttons on each analytics page.
INSIGHT_SOURCES: dict[str, tuple[str, ...]] = {
    "inventory": ("inventory_alerts", "stockout_predictions", "inventory_anomalies"),
    "accounts": ("accounts_summary", "transaction_anomalies"),
    "delivery": ("delivery_overview", "active_deliveries"),
    "organization": ("organization_overview",),
    "projects": ("projects_overview",),
}


def tools_for(permissions: set[str]) -> list[Tool]:
    return [t for t in TOOLS if t.permission is None or t.permission in permissions]
