"""
Password change and reset.

Reset tokens are random 256-bit values; only their SHA-256 hash is stored, they
expire after PASSWORD_RESET_TTL_MINUTES and work once. Any password change bumps
the user's token_version, which invalidates every previously issued JWT.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.auth.jwt_handler import create_access_token
from backend.core.auth.models import PasswordResetToken, User
from backend.core.auth.security import hash_password, verify_password
from backend.core.config import get_settings
from backend.core.mail import send_email
from backend.core.time import ensure_utc, utcnow

logger = logging.getLogger("auth.passwords")

# Self-service requests for the same account are throttled to one per window.
FORGOT_THROTTLE = timedelta(minutes=5)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _set_password(user: User, new_password: str) -> None:
    user.hashed_password = hash_password(new_password)
    user.token_version = (user.token_version or 0) + 1


def issue_token(user: User) -> str:
    return create_access_token({"sub": user.username, "ver": user.token_version or 0})


def change_password(db: Session, user: User, current_password: str, new_password: str) -> str:
    """Returns a fresh token so the current session keeps working; all others end."""
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    if current_password == new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a different password.")
    _set_password(user, new_password)
    db.commit()
    return issue_token(user)


def create_reset_link(db: Session, user: User, *, created_by: User | None = None) -> tuple[str, object]:
    """Create a one-time reset link (earlier unused links for the user are revoked)."""
    now = utcnow()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

    raw = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=get_settings().PASSWORD_RESET_TTL_MINUTES)
    db.add(PasswordResetToken(
        user_id=user.id, token_hash=_hash(raw), expires_at=expires_at,
        created_by_user_id=created_by.id if created_by else None,
    ))
    db.commit()
    url = f"{get_settings().APP_BASE_URL.rstrip('/')}/reset-password?token={quote(raw)}"
    return url, expires_at


def email_reset_link(user: User, url: str) -> bool:
    minutes = get_settings().PASSWORD_RESET_TTL_MINUTES
    return send_email(
        user.email,
        "Reset your StockPilot password",
        f"Hello {user.username},\n\n"
        f"Use this link to choose a new password (valid for {minutes} minutes, works once):\n\n{url}\n\n"
        "If you didn't ask for this, you can ignore this email; your password is unchanged.\n",
    )


def request_reset_by_email(db: Session, email: str) -> None:
    """
    Self-service "forgot password". Always behaves the same from the caller's point
    of view so it can't be used to discover which emails have accounts.
    """
    if not get_settings().email_enabled:
        logger.info("Password reset requested but SMTP is not configured; an admin must issue a link.")
        return
    user = db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()
    if user is None or not user.is_active:
        return
    recent = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id, PasswordResetToken.created_at > utcnow() - FORGOT_THROTTLE)
        .first()
    )
    if recent:
        return
    url, _ = create_reset_link(db, user)
    email_reset_link(user, url)


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired.")
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == _hash(raw_token)).first()
    if row is None or row.used_at is not None or ensure_utc(row.expires_at) < utcnow():
        raise invalid
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise invalid
    _set_password(user, new_password)
    row.used_at = utcnow()
    db.commit()
