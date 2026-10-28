from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.auth import schemas
from backend.core.auth.service import AuthService
from backend.core.auth.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=schemas.UserResponse)
def register(
    user_data: schemas.UserCreate,
    db: Session = Depends(DatabaseAdapter.get_db)
):
    return AuthService.register_user(db, user_data)


@router.post("/login", response_model=schemas.Token)
def login(
    login_data: schemas.UserLogin,
    db: Session = Depends(DatabaseAdapter.get_db)
):
    return AuthService.authenticate_user(db, login_data)


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return current_user