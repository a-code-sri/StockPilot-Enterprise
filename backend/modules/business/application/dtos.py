from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class BusinessProfileUpdateDTO(BaseModel):
    legal_name: str = Field(min_length=2, max_length=200)
    trade_name: Optional[str] = Field(default=None, max_length=200)
    gstin: Optional[str] = Field(default=None, max_length=20)
    pan: Optional[str] = Field(default=None, max_length=12)
    cin: Optional[str] = Field(default=None, max_length=25)
    state_code: Optional[str] = Field(default=None, pattern=r"^[0-9]{2}$")
    address: Optional[str] = Field(default=None, max_length=1000)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)


class RegistrationCheckDTO(BaseModel):
    legal_name: str = ""
    gstin: Optional[str] = None
    pan: Optional[str] = None
    cin: Optional[str] = None
    state_code: Optional[str] = None


class ReviewDTO(BaseModel):
    decision: Literal["approve", "reject"]
    notes: Optional[str] = Field(default=None, max_length=2000)


class BusinessProfileDTO(BaseModel):
    configured: bool
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    cin: Optional[str] = None
    state_code: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    verification_status: str = "unverified"
    verification_report: Optional[dict] = None
    checked_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    updated_at: Optional[datetime] = None
