from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.auth.models import User
from backend.core.time import utcnow
from backend.modules.business.domain.registration import GST_STATES, normalise, verify_registration
from backend.modules.business.infrastructure.models import BusinessProfileModel, VerificationStatus

PROFILE_ID = 1
REGISTRATION_FIELDS = ("legal_name", "gstin", "pan", "cin", "state_code")


class BusinessService:
    """
    Verification workflow:
      save profile -> offline checks run automatically
        all checks pass  -> format_verified (awaiting review)
        any check fails  -> unverified (report lists the problems)
      admin review (business.manage) -> verified / rejected
    Changing any registration field resets the status and re-runs the checks.
    """

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> BusinessProfileModel | None:
        return self.db.get(BusinessProfileModel, PROFILE_ID)

    def to_dict(self, p: BusinessProfileModel | None) -> dict:
        if p is None:
            return {"configured": False}
        reviewer = self.db.get(User, p.reviewed_by_user_id) if p.reviewed_by_user_id else None
        return {
            "configured": True,
            "legal_name": p.legal_name,
            "trade_name": p.trade_name,
            "gstin": p.gstin,
            "pan": p.pan,
            "cin": p.cin,
            "state_code": p.state_code,
            "state": GST_STATES.get(p.state_code or ""),
            "address": p.address,
            "email": p.email,
            "phone": p.phone,
            "verification_status": p.verification_status.value,
            "verification_report": p.verification_report,
            "checked_at": p.checked_at,
            "reviewed_by": reviewer.username if reviewer else None,
            "reviewed_at": p.reviewed_at,
            "review_notes": p.review_notes,
            "updated_at": p.updated_at,
        }

    @staticmethod
    def check(dto) -> dict:
        return verify_registration(
            legal_name=dto.legal_name, gstin=dto.gstin, pan=dto.pan, cin=dto.cin, state_code=dto.state_code
        ).as_dict()

    def save(self, dto) -> BusinessProfileModel:
        profile = self.get()
        values = {
            "legal_name": dto.legal_name.strip(),
            "trade_name": (dto.trade_name or "").strip() or None,
            "gstin": normalise(dto.gstin) or None,
            "pan": normalise(dto.pan) or None,
            "cin": normalise(dto.cin) or None,
            "state_code": dto.state_code or None,
            "address": dto.address,
            "email": str(dto.email).lower() if dto.email else None,
            "phone": dto.phone,
        }
        # A GSTIN implies the PAN and state; fill them in when omitted.
        if values["gstin"] and len(values["gstin"]) == 15:
            values["pan"] = values["pan"] or values["gstin"][2:12]
            values["state_code"] = values["state_code"] or values["gstin"][:2]

        registration_changed = profile is None or any(
            getattr(profile, f) != values[f] for f in REGISTRATION_FIELDS
        )

        if profile is None:
            profile = BusinessProfileModel(id=PROFILE_ID, **values)
            self.db.add(profile)
        else:
            for k, v in values.items():
                setattr(profile, k, v)

        if registration_changed or profile.verification_status == VerificationStatus.unverified:
            report = verify_registration(
                legal_name=values["legal_name"], gstin=values["gstin"], pan=values["pan"], cin=values["cin"],
                state_code=values["state_code"],
            ).as_dict()
            profile.verification_report = report
            profile.checked_at = utcnow()
            profile.verification_status = (
                VerificationStatus.format_verified if report["valid"] else VerificationStatus.unverified
            )
            profile.reviewed_by_user_id = None
            profile.reviewed_at = None
            profile.review_notes = None

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def review(self, decision: str, notes: str | None, reviewer) -> BusinessProfileModel:
        profile = self.get()
        if profile is None:
            raise HTTPException(status_code=404, detail="Business profile has not been set up yet.")
        if decision == "approve" and not (profile.verification_report or {}).get("valid"):
            raise HTTPException(
                status_code=409,
                detail="Registration numbers failed the automatic checks. Fix them before approving.",
            )

        profile.verification_status = (
            VerificationStatus.verified if decision == "approve" else VerificationStatus.rejected
        )
        profile.reviewed_by_user_id = reviewer.id
        profile.reviewed_at = utcnow()
        profile.review_notes = notes
        self.db.commit()
        self.db.refresh(profile)
        return profile
