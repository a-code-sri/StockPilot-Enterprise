import os
import sys
import importlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Ensure `import backend...` works regardless of where Alembic is launched from ---
ALEMBIC_DIR = os.path.dirname(__file__)  # .../backend/alembic
BACKEND_DIR = os.path.abspath(os.path.join(ALEMBIC_DIR, ".."))  # .../backend
REPO_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))    # project root

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import Base (shared metadata)
from backend.core.database.base import Base  # noqa: E402


# -------------------------
# IMPORTANT: import models
# -------------------------
# Alembic autogenerate only "sees" tables that are registered into Base.metadata.
# Registration happens when the Python modules defining those models are imported.
def _import_required(module_path: str) -> None:
    try:
        importlib.import_module(module_path)
    except Exception as e:
        raise RuntimeError(
            f"Alembic could not import required module '{module_path}'. "
            f"This prevents autogenerate from seeing all tables.\n"
            f"Original error: {e}"
        ) from e


# Outbox table model
_import_required("backend.outbox.models")

# Domain models + projection (analytics) models for each module
_import_required("backend.modules.accounts.infrastructure.models")
_import_required("backend.modules.accounts.infrastructure.projections")

_import_required("backend.modules.inventory.infrastructure.models")
_import_required("backend.modules.inventory.infrastructure.projections")

_import_required("backend.modules.delivery.infrastructure.models")
_import_required("backend.modules.delivery.infrastructure.projections")

_import_required("backend.modules.organization.infrastructure.models")
_import_required("backend.modules.organization.infrastructure.projections")

_import_required("backend.modules.projects.infrastructure.models")
_import_required("backend.modules.projects.infrastructure.projections")


# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL env var is not set. Example:\n"
            "postgresql+psycopg2://user:pass@host:5432/dbname"
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()