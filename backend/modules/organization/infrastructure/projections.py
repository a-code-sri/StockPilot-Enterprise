from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from backend.core.database.base import Base


class OrganizationOverviewSnapshot(Base):
    """
    Stores a cached "overview" payload the frontend needs, keyed by histogram_bins.
    Snapshot gets recomputed asynchronously by the analytics worker when org changes.
    """
    __tablename__ = "org_overview_snapshot"

    histogram_bins = Column(Integer, primary_key=True)
    snapshot = Column(JSONB, nullable=False)

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())