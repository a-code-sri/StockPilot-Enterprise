from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.core.auth import models
from backend.core.auth.jwt_handler import decode_access_token
from backend.core.database.adapter import get_db

# /auth/token accepts the OAuth2 form so Swagger's "Authorize" button works.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

_unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


def user_from_token(db: Session, token: str | None) -> models.User | None:
    """Resolve an active user from a JWT, or None. Shared by REST and WebSocket auth."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    user = db.query(models.User).filter(models.User.username == payload["sub"]).first()
    if user is None or not user.is_active:
        return None
    # Tokens issued before the last password change/reset are no longer valid.
    if payload.get("ver", 0) != (user.token_version or 0):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    user = user_from_token(db, token)
    if user is None:
        raise _unauthorized
    return user
