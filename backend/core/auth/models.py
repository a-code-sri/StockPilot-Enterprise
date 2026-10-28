from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from backend.core.database.base import Base
from backend.core.rbac.models import user_roles


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    roles = relationship(
        "Role",
        secondary=user_roles,
        backref="users"
    )