from pydantic import BaseModel, EmailStr
from typing import Optional

from typing import List


class RoleResponse(BaseModel):
    name: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    roles: List[RoleResponse]

    class Config:
        from_attributes = True
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
