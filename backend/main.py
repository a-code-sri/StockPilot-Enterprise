import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import asyncio

from backend.core.realtime.router import router as realtime_router
from backend.core.realtime.listener import realtime_listener

from backend.core.auth.router import router as auth_router
from backend.core.rbac.router import router as rbac_router
from backend.core.database.session import SessionLocal
from backend.core.rbac.models import Role, Permission

# Module routers (CRUD)
from backend.modules.accounts.router import router as accounts_router
from backend.modules.inventory.router import router as inventory_router
from backend.modules.delivery.router import router as delivery_router
from backend.modules.organization.router import router as organization_router
from backend.modules.projects.router import router as projects_router

# Analytics routers
from backend.modules.accounts.analytics_router import router as accounts_analytics_router
from backend.modules.inventory.analytics_router import router as inventory_analytics_router
from backend.modules.delivery.analytics_router import router as delivery_analytics_router
from backend.modules.organization.analytics_router import router as organization_analytics_router
from backend.modules.projects.analytics_router import router as projects_analytics_router


def seed_rbac(db: Session) -> None:
    """
    Seeds permissions + ensures admin role has all permissions.
    Keep this idempotent.

    NOTE: Permissions must match strings used in require_permission(...) in routers.
    """
    permissions = [
        # Inventory (your routers use inventory.read/inventory.write)
        "inventory.read",
        "inventory.write",
        # keep these for compatibility if older code uses them
        "inventory.create",
        "inventory.update",
        "inventory.delete",

        # Accounts
        "accounts.read",
        "accounts.write",

        # Delivery
        "delivery.read",
        "delivery.write",

        # Projects
        "projects.read",
        "projects.write",

        # Organization (your org analytics/router uses require_permission("organization"))
        # Organization
        "organization",
        "organization.read",
        "organization.write",

        # RBAC
        "rbac.manage",
        "analytics.read"
    ]

    # Upsert permissions
    for perm in permissions:
        existing = db.query(Permission).filter_by(name=perm).first()
        if not existing:
            db.add(Permission(name=perm))
    db.commit()

    # Ensure admin role exists and always has ALL permissions
    all_perms = db.query(Permission).all()
    admin_role = db.query(Role).filter_by(name="admin").first()

    if not admin_role:
        admin_role = Role(name="admin", permissions=all_perms)
        db.add(admin_role)
        db.commit()
    else:
        # keep admin in sync when new permissions are added later
        admin_role.permissions = all_perms
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()

    try:
        if os.getenv("SEED_RBAC", "true").lower() in (
            "1",
            "true",
            "yes",
        ):
            seed_rbac(db)
    finally:
        db.close()

    # Start PostgreSQL -> WebSocket realtime bridge.
    realtime_listener.start(asyncio.get_running_loop())

    try:
        yield
    finally:
        realtime_listener.stop()


app = FastAPI(
    title="Business OS Backend",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routers
app.include_router(
    realtime_router,
    tags=["Realtime"],
)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(rbac_router, prefix="/rbac", tags=["RBAC"])

# Module CRUD routers
app.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
app.include_router(delivery_router, prefix="/delivery", tags=["Delivery"])
app.include_router(organization_router, prefix="/organization", tags=["Organization"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])

# Analytics routers (projection-backed)
app.include_router(accounts_analytics_router, prefix="/analytics/accounts", tags=["Accounts Analytics"])
app.include_router(inventory_analytics_router, prefix="/analytics/inventory", tags=["Inventory Analytics"])
app.include_router(delivery_analytics_router, prefix="/analytics/delivery", tags=["Delivery Analytics"])
app.include_router(organization_analytics_router, prefix="/analytics/organization", tags=["Organization Analytics"])
app.include_router(projects_analytics_router, prefix="/analytics/projects", tags=["Projects Analytics"])


@app.get("/")
def health_check():
    return {"status": "Backend Running"}