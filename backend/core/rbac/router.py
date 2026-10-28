from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac import schemas , models
from backend.core.rbac.service import RBACService
from backend.core.rbac.dependencies import require_permission

router = APIRouter()

@router.get("/", response_model=list[schemas.RoleResponse])
def get_roles(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("rbac.manage"))
):
    return db.query(models.Role).order_by(models.Role.name).all()

# ✅ Create Role
@router.post("/", response_model=schemas.RoleResponse)
def create_role(
    role_data: schemas.RoleCreate,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("rbac.manage"))
):
    return RBACService.create_role(
    db,
    role_data.name,
    role_data.access
)


# ✅ Update Role Permissions
@router.put("/{role_name}", response_model=schemas.RoleResponse)
def update_role(
    role_name: str,
    role_data: schemas.RoleUpdate,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("rbac.manage"))
):
    return RBACService.update_role_permissions(
        db,
        role_name,
        role_data.permissions
    )


# ✅ Delete Role
@router.delete("/{role_name}")
def delete_role(
    role_name: str,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("rbac.manage"))
):
    return RBACService.delete_role(db, role_name)