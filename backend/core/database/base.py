from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Ensure Alembic discovers all tables (imports register models on Base.metadata)

# Core / RBAC models
try:
    from backend.core.rbac import models as _rbac_models  # noqa: F401
except Exception:
    pass

try:
    from backend.core.auth import models as _auth_models  # noqa: F401
except Exception:
    pass

# Module models
try:
    from backend.modules.accounts.infrastructure import models as _accounts_models  # noqa: F401
except Exception:
    pass

try:
    from backend.modules.inventory.infrastructure import models as _inventory_models  # noqa: F401
except Exception:
    pass

try:
    from backend.modules.organization.infrastructure import models as _organization_models  # noqa: F401
except Exception:
    pass

try:
    from backend.modules.delivery.infrastructure import models as _delivery_models  # noqa: F401
except Exception:
    pass

# Outbox models
try:
    from backend.outbox import models as _outbox_models  # noqa: F401
except Exception:
    pass
# Accounts projection models (analytics read-model)
try:
    from backend.modules.accounts.infrastructure import projections as _accounts_projections  # noqa: F401
except Exception:
    pass