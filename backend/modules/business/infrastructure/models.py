import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from backend.core.database.base import Base
from backend.core.time import utcnow


class VerificationStatus(str, enum.Enum):
    unverified = "unverified"          # profile saved, numbers failed offline checks or none given
    format_verified = "format_verified"  # offline checks passed; awaiting admin review
    verified = "verified"              # admin confirmed against registration documents
    rejected = "rejected"              # admin rejected; see review_notes


class BusinessProfileModel(Base):
    """The business that operates this StockPilot installation (single row, id=1)."""

    __tablename__ = "business_profile"

    id = Column(Integer, primary_key=True)
    legal_name = Column(String(200), nullable=False)
    trade_name = Column(String(200), nullable=True)
    gstin = Column(String(15), nullable=True)
    pan = Column(String(10), nullable=True)
    cin = Column(String(21), nullable=True)
    state_code = Column(String(2), nullable=True)
    address = Column(Text, nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(30), nullable=True)

    verification_status = Column(
        Enum(VerificationStatus, name="business_verification_status"),
        nullable=False,
        default=VerificationStatus.unverified,
    )
    # Result of the most recent offline check: {"valid", "errors", "warnings", "details"}
    verification_report = Column(JSONB, nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=True)

    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (CheckConstraint("id = 1", name="ck_business_profile_single_row"),)
