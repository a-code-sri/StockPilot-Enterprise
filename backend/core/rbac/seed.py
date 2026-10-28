from sqlalchemy.orm import Session
from backend.core.rbac.models import Role, Permission


def seed_rbac(db: Session):
    permissions = [
        "inventory.create",
        "inventory.read",
        "inventory.update",
        "inventory.delete",
        "accounts.read",
        "delivery.read"
    ]

    permission_objs = []

    for perm in permissions:
        existing = db.query(Permission).filter_by(name=perm).first()
        if not existing:
            p = Permission(name=perm)
            db.add(p)
            permission_objs.append(p)
        else:
            permission_objs.append(existing)

    admin_role = db.query(Role).filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", permissions=permission_objs)
        db.add(admin_role)

    db.commit()