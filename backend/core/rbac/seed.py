"""
Idempotent RBAC seeding and admin bootstrap. Runs on API startup.
"""

import logging

from sqlalchemy.orm import Session

from backend.core.auth.models import User
from backend.core.auth.security import hash_password
from backend.core.config import Settings
from backend.core.rbac.models import Permission, Role
from backend.core.rbac.permissions import ADMIN_ROLE, LEGACY_PERMISSIONS, PERMISSIONS

logger = logging.getLogger("rbac.seed")


def seed_rbac(db: Session) -> None:
    existing = {p.name: p for p in db.query(Permission).all()}

    for name in PERMISSIONS:
        if name not in existing:
            existing[name] = Permission(name=name)
            db.add(existing[name])
    db.flush()

    # Move roles off legacy permission names, then delete them.
    for legacy, replacements in LEGACY_PERMISSIONS.items():
        legacy_perm = existing.get(legacy)
        if legacy_perm is None:
            continue
        for role in list(legacy_perm.roles):
            for repl in replacements:
                if existing[repl] not in role.permissions:
                    role.permissions.append(existing[repl])
            role.permissions.remove(legacy_perm)
        db.delete(legacy_perm)
        logger.info("Removed legacy permission '%s'", legacy)

    # Admin role always holds the whole catalog (also short-circuited in RBACService).
    admin = db.query(Role).filter_by(name=ADMIN_ROLE).first()
    catalog = [existing[n] for n in PERMISSIONS]
    if admin is None:
        db.add(Role(name=ADMIN_ROLE, permissions=catalog))
    else:
        admin.permissions = catalog

    db.commit()


def bootstrap_admin(db: Session, settings: Settings) -> None:
    """Create/upgrade the configured admin user so a fresh install is usable."""
    if not (settings.ADMIN_USERNAME and settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD):
        if not db.query(User).join(User.roles).filter(Role.name == ADMIN_ROLE).first():
            logger.warning(
                "No admin user exists. Set ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD, or run "
                "`python -m backend.scripts.create_admin`."
            )
        return

    admin_role = db.query(Role).filter_by(name=ADMIN_ROLE).one()
    user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()

    if user is None:
        user = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL.lower(),
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            is_active=True,
        )
        db.add(user)
        logger.info("Created bootstrap admin user '%s'", settings.ADMIN_USERNAME)

    if admin_role not in user.roles:
        user.roles.append(admin_role)
    user.is_active = True
    db.commit()
