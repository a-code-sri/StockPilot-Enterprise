from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from backend.core.auth.models import User
from backend.core.database.adapter import get_db
from backend.core.rbac import models, schemas
from backend.core.rbac.dependencies import require_permission
from backend.core.rbac.permissions import MODULES, PERMISSIONS
from backend.core.rbac.service import RBACService

router = APIRouter()

manage = require_permission("rbac.manage")


def _user_row(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "roles": sorted(r.name for r in user.roles),
    }


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------- Permission catalog ----------------

@router.get("/permissions", response_model=schemas.PermissionCatalogResponse)
def permission_catalog(user=Depends(manage)):
    return {"modules": {m: list(a) for m, a in MODULES.items()}, "permissions": list(PERMISSIONS)}


# ---------------- Roles ----------------

@router.get("/", response_model=list[schemas.RoleResponse])
def get_roles(db: Session = Depends(get_db), user=Depends(manage)):
    return db.query(models.Role).options(selectinload(models.Role.permissions)).order_by(models.Role.name).all()


@router.post("/", response_model=schemas.RoleResponse, status_code=201)
def create_role(role_data: schemas.RoleCreate, db: Session = Depends(get_db), user=Depends(manage)):
    return RBACService.create_role(db, role_data.name, role_data.access)


@router.put("/{role_name}", response_model=schemas.RoleResponse)
def update_role(role_name: str, role_data: schemas.RoleUpdate, db: Session = Depends(get_db), user=Depends(manage)):
    return RBACService.update_role_permissions(db, role_name, role_data.permissions)


@router.delete("/{role_name}")
def delete_role(role_name: str, db: Session = Depends(get_db), user=Depends(manage)):
    return RBACService.delete_role(db, role_name)


# ---------------- Users ----------------

@router.get("/users", response_model=list[schemas.UserAdminResponse])
def list_users(db: Session = Depends(get_db), user=Depends(manage)):
    users = db.query(User).options(selectinload(User.roles)).order_by(User.username).all()
    return [_user_row(u) for u in users]


@router.put("/users/{user_id}/roles", response_model=schemas.UserAdminResponse)
def set_user_roles(
    user_id: int,
    body: schemas.UserRolesUpdate,
    db: Session = Depends(get_db),
    acting_user=Depends(manage),
):
    target = _get_user(db, user_id)
    return _user_row(RBACService.set_user_roles(db, target, body.roles, acting_user))


@router.patch("/users/{user_id}", response_model=schemas.UserAdminResponse)
def set_user_status(
    user_id: int,
    body: schemas.UserStatusUpdate,
    db: Session = Depends(get_db),
    acting_user=Depends(manage),
):
    target = _get_user(db, user_id)
    return _user_row(RBACService.set_user_active(db, target, body.is_active, acting_user))
