from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from backend.core.database.base import Base


class OrganizationOverviewSnapshot(Base):
    """
    Cached organization overview, rebuilt by the worker whenever the org changes.
    One row (key 0). The column keeps its historical name `histogram_bins`; the
    histogram itself is now computed per request from the stored salary list.
    """

    __tablename__ = "org_overview_snapshot"

    histogram_bins = Column(Integer, primary_key=True)
    snapshot = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
