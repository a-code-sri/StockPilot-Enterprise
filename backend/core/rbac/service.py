from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.core.rbac.models import Permission, Role
from backend.core.rbac.permissions import ADMIN_ROLE, PERMISSIONS


def _is_admin(user) -> bool:
    return any(role.name == ADMIN_ROLE for role in user.roles)


class RBACService:

    @staticmethod
    def get_user_permissions(user) -> set[str]:
        if _is_admin(user):
            return set(PERMISSIONS)
        return {perm.name for role in user.roles for perm in role.permissions}

    @staticmethod
    def has_permission(user, permission: str) -> bool:
        return _is_admin(user) or permission in RBACService.get_user_permissions(user)

    # ---------------- Roles ----------------

    @staticmethod
    def _resolve_permissions(db: Session, names: list[str]) -> list[Permission]:
        names = sorted(set(names))
        unknown = [n for n in names if n not in PERMISSIONS]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown permission(s): {', '.join(unknown)}")
        perms = db.query(Permission).filter(Permission.name.in_(names)).all()
        if len(perms) != len(names):
            # Catalog not seeded yet.
            raise HTTPException(status_code=500, detail="Permission catalog is not seeded")
        return perms

    @staticmethod
    def create_role(db: Session, name: str, access: dict[str, list[str]]) -> Role:
        name = name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Role name is required")
        if name.lower() == ADMIN_ROLE:
            raise HTTPException(status_code=400, detail="Admin role cannot be recreated")
        if db.query(Role).filter(Role.name == name).first():
            raise HTTPException(status_code=409, detail="Role already exists")

        names = [f"{module}.{action}" for module, actions in access.items() for action in actions]
        role = Role(name=name, permissions=RBACService._resolve_permissions(db, names))
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def _get_mutable_role(db: Session, role_name: str) -> Role:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        if role.name == ADMIN_ROLE:
            raise HTTPException(status_code=400, detail="Admin role cannot be modified")
        return role

    @staticmethod
    def update_role_permissions(db: Session, role_name: str, permission_names: list[str]) -> Role:
        role = RBACService._get_mutable_role(db, role_name)
        role.permissions = RBACService._resolve_permissions(db, permission_names)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def delete_role(db: Session, role_name: str) -> dict:
        role = RBACService._get_mutable_role(db, role_name)
        db.delete(role)
        db.commit()
        return {"detail": "Role deleted successfully"}

    # ---------------- Users ----------------

    @staticmethod
    def _active_admin_count(db: Session) -> int:
        from backend.core.auth.models import User

        return (
            db.query(User)
            .join(User.roles)
            .filter(Role.name == ADMIN_ROLE, User.is_active.is_(True))
            .count()
        )

    @staticmethod
    def set_user_roles(db: Session, user, role_names: list[str], acting_user):
        roles = db.query(Role).filter(Role.name.in_(set(role_names))).all()
        missing = sorted(set(role_names) - {r.name for r in roles})
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown role(s): {', '.join(missing)}")

        removing_admin = _is_admin(user) and ADMIN_ROLE not in role_names
        if removing_admin and user.is_active and RBACService._active_admin_count(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last active admin")
        if removing_admin and user.id == acting_user.id:
            raise HTTPException(status_code=400, detail="You cannot remove your own admin role")

        user.roles = roles
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def set_user_active(db: Session, user, is_active: bool, acting_user):
        if not is_active:
            if user.id == acting_user.id:
                raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
            if _is_admin(user) and user.is_active and RBACService._active_admin_count(db) <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate the last active admin")
        user.is_active = is_active
        db.commit()
        db.refresh(user)
        return user
