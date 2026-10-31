from typing import Annotated, List, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def _bcrypt_limit(v: str) -> str:
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes.")
    return v


NewPassword = Annotated[str, Field(min_length=8, max_length=128), AfterValidator(_bcrypt_limit)]


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    is_active: bool = True
    roles: List[RoleResponse]
    # Effective permissions (union over roles; admins get the full catalog).
    permissions: List[str] = []


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: NewPassword


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: NewPassword


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: NewPassword


class AuthOptions(BaseModel):
    registration_enabled: bool
    email_enabled: bool
