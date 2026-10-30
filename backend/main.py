import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.core.config import get_settings
from backend.core.database.registry import import_all_models

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("main")

# Register every model before routers import them, so relationships resolve.
import_all_models()

from backend.core.auth.router import router as auth_router  # noqa: E402
from backend.core.database.session import SessionLocal  # noqa: E402
from backend.core.rbac.router import router as rbac_router  # noqa: E402
from backend.core.rbac.seed import bootstrap_admin, seed_rbac  # noqa: E402
from backend.core.realtime.listener import realtime_listener  # noqa: E402
from backend.core.realtime.router import router as realtime_router  # noqa: E402
from backend.modules.accounts.analytics_router import router as accounts_analytics_router  # noqa: E402
from backend.modules.accounts.router import router as accounts_router  # noqa: E402
from backend.modules.ai.router import router as ai_router  # noqa: E402
from backend.modules.business.router import router as business_router  # noqa: E402
from backend.modules.delivery.analytics_router import router as delivery_analytics_router  # noqa: E402
from backend.modules.delivery.router import router as delivery_router  # noqa: E402
from backend.modules.inventory.analytics_router import router as inventory_analytics_router  # noqa: E402
from backend.modules.inventory.router import router as inventory_router  # noqa: E402
from backend.modules.organization.analytics_router import router as organization_analytics_router  # noqa: E402
from backend.modules.organization.router import router as organization_router  # noqa: E402
from backend.modules.projects.analytics_router import router as projects_analytics_router  # noqa: E402
from backend.modules.projects.router import router as projects_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SEED_RBAC:
        db = SessionLocal()
        try:
            seed_rbac(db)
            bootstrap_admin(db, settings)
        finally:
            db.close()

    realtime_listener.start(asyncio.get_running_loop())
    try:
        yield
    finally:
        realtime_listener.stop()


app = FastAPI(
    title="StockPilot Enterprise API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(realtime_router, tags=["Realtime"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(rbac_router, prefix="/rbac", tags=["RBAC"])
app.include_router(business_router, prefix="/business", tags=["Business"])
app.include_router(ai_router, prefix="/ai", tags=["AI"])

app.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
app.include_router(delivery_router, prefix="/delivery", tags=["Delivery"])
app.include_router(organization_router, prefix="/organization", tags=["Organization"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])

app.include_router(accounts_analytics_router, prefix="/analytics/accounts", tags=["Accounts Analytics"])
app.include_router(inventory_analytics_router, prefix="/analytics/inventory", tags=["Inventory Analytics"])
app.include_router(delivery_analytics_router, prefix="/analytics/delivery", tags=["Delivery Analytics"])
app.include_router(organization_analytics_router, prefix="/analytics/organization", tags=["Organization Analytics"])
app.include_router(projects_analytics_router, prefix="/analytics/projects", tags=["Projects Analytics"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "stockpilot-api"}


@app.get("/health", tags=["Health"])
def health():
    """Liveness + dependency status (used by Docker health checks)."""
    db_ok = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "realtime_listener": realtime_listener.is_running}
