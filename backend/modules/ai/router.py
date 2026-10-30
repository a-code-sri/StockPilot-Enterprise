from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.core.rbac.permissions import MODULE_READ_PERMISSION
from backend.core.rbac.service import RBACService
from backend.modules.ai.assistant import Assistant
from backend.modules.ai.client import AIUnavailable, OllamaClient

router = APIRouter()

can_use_ai = require_permission("ai.use")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(min_length=1, max_length=50)


class InsightRequest(BaseModel):
    module: Literal["inventory", "accounts", "delivery", "organization", "projects"]


def _assistant(db: Session, user) -> Assistant:
    return Assistant(db, user, RBACService.get_user_permissions(user))


@router.get("/status")
def ai_status(user=Depends(get_current_user)):
    """Whether AI features are usable (shown in the UI before offering them)."""
    status = OllamaClient().status()
    status["can_use"] = RBACService.has_permission(user, "ai.use")
    return status


@router.post("/chat")
def chat(body: ChatRequest, db: Session = Depends(get_db), user=Depends(can_use_ai)):
    try:
        return _assistant(db, user).chat([m.model_dump() for m in body.messages])
    except AIUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/insights")
def insights(body: InsightRequest, db: Session = Depends(get_db), user=Depends(can_use_ai)):
    if not RBACService.has_permission(user, MODULE_READ_PERMISSION[body.module]):
        raise HTTPException(status_code=403, detail=f"Missing permission: {MODULE_READ_PERMISSION[body.module]}")
    try:
        return _assistant(db, user).insights(body.module)
    except AIUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
