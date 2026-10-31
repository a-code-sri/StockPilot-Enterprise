from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    # {"inventory": ["read", "write"], ...}
    access: Dict[str, List[str]]


class RoleUpdate(BaseModel):
    permissions: List[str]


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    permissions: List[PermissionResponse]


class UserRolesUpdate(BaseModel):
    roles: List[str]


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserAdminResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    roles: List[str]


class PermissionCatalogResponse(BaseModel):
    modules: Dict[str, List[str]]
    permissions: List[str]


class ResetLinkResponse(BaseModel):
    reset_url: str
    expires_at: datetime
    emailed: bool
