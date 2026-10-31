"""
Integration tests against a real PostgreSQL database.

    TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/stockpilot_test pytest tests/integration

The database is wiped (schema recreated + migrations applied) at session start.
Never point this at a database you care about.
"""

import os
from pathlib import Path

import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("TEST_DATABASE_URL not set; skipping integration tests", allow_module_level=True)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from backend.core.auth.models import User  # noqa: E402
from backend.core.auth.security import hash_password  # noqa: E402
from backend.core.database.base import Base  # noqa: E402
from backend.core.database.session import SessionLocal, engine  # noqa: E402
from backend.core.rbac.models import Role  # noqa: E402
from backend.core.rbac.seed import seed_rbac  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ADMIN = {"username": "admin", "password": "admin-pass-123", "email": "admin@test.local"}


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(str(ROOT / "backend" / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables(migrated_database):
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    db = SessionLocal()
    try:
        seed_rbac(db)
        admin_role = db.query(Role).filter_by(name="admin").one()
        db.add(User(username=ADMIN["username"], email=ADMIN["email"],
                    hashed_password=hash_password(ADMIN["password"]), is_active=True, roles=[admin_role]))
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture(scope="session")
def client():
    from backend.main import app

    with TestClient(app) as c:
        yield c


def login(client, username, password) -> dict:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return login(client, ADMIN["username"], ADMIN["password"])


@pytest.fixture
def run_worker():
    """Process all pending outbox events synchronously; returns rows by status."""
    from backend.workers.analytics_worker import process_pending_once

    def _run():
        process_pending_once()
        with engine.connect() as conn:
            return dict(conn.execute(text("SELECT status, count(*) FROM analytics_outbox GROUP BY status")).all())

    return _run
