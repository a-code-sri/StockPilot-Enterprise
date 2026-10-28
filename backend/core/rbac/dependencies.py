from fastapi import Depends, HTTPException, status

from backend.core.auth.dependencies import get_current_user
from backend.core.rbac.service import RBACService


def require_permission(permission: str):
    def permission_checker(current_user=Depends(get_current_user)):
        if not RBACService.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return permission_checker