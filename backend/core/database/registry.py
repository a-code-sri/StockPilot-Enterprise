"""
Imports every model module so all tables are registered on Base.metadata and all
string-based relationships (e.g. ProjectModel.resources -> "EmployeeModel") can be
resolved. Call this once at process start (API, worker, Alembic, scripts).

Import errors propagate on purpose: a broken model must fail loudly.
"""

import importlib

MODEL_MODULES = (
    "backend.core.rbac.models",
    "backend.core.auth.models",
    "backend.outbox.models",
    "backend.modules.accounts.infrastructure.models",
    "backend.modules.accounts.infrastructure.projections",
    "backend.modules.inventory.infrastructure.models",
    "backend.modules.inventory.infrastructure.projections",
    "backend.modules.delivery.infrastructure.models",
    "backend.modules.delivery.infrastructure.projections",
    "backend.modules.organization.infrastructure.models",
    "backend.modules.organization.infrastructure.projections",
    "backend.modules.projects.infrastructure.models",
    "backend.modules.projects.infrastructure.projections",
    "backend.modules.business.infrastructure.models",
)


def import_all_models() -> None:
    for module_path in MODEL_MODULES:
        importlib.import_module(module_path)
