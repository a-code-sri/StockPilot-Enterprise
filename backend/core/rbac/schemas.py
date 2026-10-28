from pydantic import BaseModel
from typing import List , Dict


class PermissionResponse(BaseModel):
    name: str

    class Config:
        from_attributes = True



class RoleCreate(BaseModel):
    name: str
    access: Dict[str, List[str]]


class RoleUpdate(BaseModel):
    permissions: List[str]


class RoleResponse(BaseModel):
    id: int
    name: str
    permissions: List[PermissionResponse]

    class Config:
        from_attributes = True