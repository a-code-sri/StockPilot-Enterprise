import sqlalchemy as sa
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB

from backend.core.database.base import Base


class ProjectsPortfolioSnapshot(Base):
    """
    Single-row snapshot for the whole portfolio.
    Convention: row with id=1.
    """
    __tablename__ = "projects_portfolio_snapshot"

    id = Column(Integer, primary_key=True)  # use 1
    snapshot = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))

    generated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        Index("ix_projects_portfolio_snapshot_updated_at", "updated_at"),
    )


class ProjectSnapshot(Base):
    """
    Per-project snapshot. One row per project.
    """
    __tablename__ = "project_snapshot"

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    snapshot = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))

    generated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        Index("ix_project_snapshot_updated_at", "updated_at"),
    )