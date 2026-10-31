from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.core.auth import schemas
from backend.core.auth.dependencies import get_current_user
from backend.core.auth.service import AuthService
from backend.core.config import get_settings
from backend.core.database.adapter import get_db
from backend.core.rbac.service import RBACService

router = APIRouter()


def user_payload(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "roles": [{"name": r.name} for r in user.roles],
        "permissions": sorted(RBACService.get_user_permissions(user)),
    }


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    if not get_settings().ALLOW_REGISTRATION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Self-registration is disabled")
    return user_payload(AuthService.register_user(db, user_data))


@router.post("/login", response_model=schemas.Token)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """JSON login used by the web app and the Streamlit client."""
    return AuthService.authenticate_user(db, login_data.username, login_data.password)


@router.post("/token", response_model=schemas.Token, include_in_schema=False)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Form-encoded login for Swagger UI's Authorize dialog."""
    return AuthService.authenticate_user(db, form.username, form.password)


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return user_payload(current_user)
