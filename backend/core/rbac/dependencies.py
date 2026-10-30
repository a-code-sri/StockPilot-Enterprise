from fastapi import Depends, HTTPException, status

from backend.core.auth.dependencies import get_current_user
from backend.core.rbac.permissions import PERMISSIONS
from backend.core.rbac.service import RBACService


def require_permission(permission: str):
    if permission not in PERMISSIONS:
        # Fail at import time instead of silently returning 403 forever.
        raise ValueError(f"Unknown permission '{permission}'. Add it to backend/core/rbac/permissions.py.")

    def permission_checker(current_user=Depends(get_current_user)):
        if not RBACService.has_permission(current_user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")
        return current_user

    return permission_checker
