from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import relationship

from backend.core.database.base import Base
from backend.core.rbac.models import user_roles
from backend.core.time import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    # Embedded in every JWT ("ver"); bumping it signs the user out everywhere
    # (done on password change/reset).
    token_version = Column(Integer, nullable=False, default=0, server_default=text("0"))

    roles = relationship("Role", secondary=user_roles, backref="users")


class PasswordResetToken(Base):
    """One-time password reset link. Only a SHA-256 hash of the token is stored."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
