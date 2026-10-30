from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.auth import models, schemas
from backend.core.auth.jwt_handler import create_access_token
from backend.core.auth.security import hash_password, verify_password


class AuthService:

    @staticmethod
    def register_user(db: Session, user_data: schemas.UserCreate) -> models.User:
        username = user_data.username.strip()
        email = str(user_data.email).strip().lower()

        if db.query(models.User).filter(func.lower(models.User.username) == username.lower()).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

        if db.query(models.User).filter(func.lower(models.User.email) == email).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        new_user = models.User(
            email=email,
            username=username,
            hashed_password=hash_password(user_data.password),
            is_active=True,
        )
        db.add(new_user)
        try:
            db.commit()
        except IntegrityError:
            # Lost a race with a concurrent registration.
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already registered")
        db.refresh(new_user)
        return new_user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> dict:
        user = db.query(models.User).filter(models.User.username == username.strip()).first()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

        return {"access_token": create_access_token(data={"sub": user.username}), "token_type": "bearer"}
