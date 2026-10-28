from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.core.auth import models, schemas
from backend.core.auth.security import hash_password, verify_password
from backend.core.auth.jwt_handler import create_access_token


class AuthService:

    @staticmethod
    def register_user(db: Session, user_data: schemas.UserCreate):
        existing_user = db.query(models.User).filter(
            models.User.username == user_data.username
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        new_user = models.User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hash_password(user_data.password)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user

    @staticmethod
    def authenticate_user(db: Session, login_data: schemas.UserLogin):
        user = db.query(models.User).filter(
            models.User.username == login_data.username
        ).first()

        if not user or not verify_password(
            login_data.password,
            user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        access_token = create_access_token(
            data={"sub": user.username}
        )

        return {"access_token": access_token, "token_type": "bearer"}