from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.core.rbac.models import Role, Permission


class RBACService:

    @staticmethod
    def get_user_permissions(user) -> set:
        permissions = set()

        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.name)

        return permissions

    @staticmethod
    def has_permission(user, permission: str) -> bool:
        # Admin shortcut (admin always has full access)
        for role in user.roles:
            if role.name == "admin":
                return True

        return permission in RBACService.get_user_permissions(user)

    # ✅ Create Role
    @staticmethod
    def create_role(db: Session, name: str, access: dict):

        if name.lower() == "admin":
            raise HTTPException(status_code=400, detail="Admin role cannot be recreated")

        existing = db.query(Role).filter(Role.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Role already exists")

        permission_names = []

        for module, actions in access.items():
            for action in actions:
                permission_names.append(f"{module}.{action}")

        permissions = db.query(Permission).filter(
            Permission.name.in_(permission_names)
        ).all()

        role = Role(name=name, permissions=permissions)
        db.add(role)
        db.commit()
        db.refresh(role)

        return role
    # ✅ Update Role Permissions
    @staticmethod
    def update_role_permissions(db: Session, role_name: str, permission_names: list):
        role = db.query(Role).filter(Role.name == role_name).first()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        if role.name == "admin":
            raise HTTPException(
                status_code=400,
                detail="Admin role permissions cannot be modified"
            )

        permissions = db.query(Permission).filter(
            Permission.name.in_(permission_names)
        ).all()

        if len(permissions) != len(permission_names):
            raise HTTPException(
                status_code=400,
                detail="One or more permissions are invalid"
            )

        role.permissions = permissions
        db.commit()
        db.refresh(role)

        return role

    # ✅ Delete Role
    @staticmethod
    def delete_role(db: Session, role_name: str):
        role = db.query(Role).filter(Role.name == role_name).first()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        if role.name == "admin":
            raise HTTPException(
                status_code=400,
                detail="Admin role cannot be deleted"
            )

        db.delete(role)
        db.commit()

        return {"detail": "Role deleted successfully"}