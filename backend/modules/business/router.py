from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.modules.business.application.dtos import (
    BusinessProfileDTO,
    BusinessProfileUpdateDTO,
    RegistrationCheckDTO,
    ReviewDTO,
)
from backend.modules.business.application.services import BusinessService
from backend.modules.business.domain.registration import GST_STATES

router = APIRouter()

can_manage = require_permission("business.manage")


@router.get("/profile", response_model=BusinessProfileDTO)
def get_profile(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Any signed-in user can see the business identity and its verification badge."""
    svc = BusinessService(db)
    return svc.to_dict(svc.get())


@router.put("/profile", response_model=BusinessProfileDTO)
def save_profile(dto: BusinessProfileUpdateDTO, db: Session = Depends(get_db), user=Depends(can_manage)):
    """Create or update the profile. Registration numbers are re-checked automatically."""
    svc = BusinessService(db)
    return svc.to_dict(svc.save(dto))


@router.post("/profile/review", response_model=BusinessProfileDTO)
def review_profile(dto: ReviewDTO, db: Session = Depends(get_db), user=Depends(can_manage)):
    """Final, human step: confirm (or reject) the registration after checking the certificates."""
    svc = BusinessService(db)
    return svc.to_dict(svc.review(dto.decision, dto.notes, user))


@router.post("/validate")
def validate_numbers(dto: RegistrationCheckDTO, user=Depends(get_current_user)):
    """Dry-run the offline checks (used for live form feedback); nothing is saved."""
    return BusinessService.check(dto)


@router.get("/states")
def gst_states():
    return [{"code": code, "name": name} for code, name in GST_STATES.items()]
