from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.auth.dependencies import user_from_token
from backend.core.database.session import SessionLocal
from backend.core.rbac.service import RBACService
from backend.core.realtime.manager import manager

logger = logging.getLogger("realtime")

router = APIRouter()

AUTH_TIMEOUT_SECONDS = 10


def _authenticate(token: str | None) -> set[str] | None:
    """Returns the user's permissions, or None if the token is invalid."""
    db = SessionLocal()
    try:
        user = user_from_token(db, token)
        return None if user is None else RBACService.get_user_permissions(user)
    finally:
        db.close()


@router.websocket("/ws/realtime")
async def realtime_websocket(websocket: WebSocket) -> None:
    """
    Authenticated, notification-only WebSocket.

    Protocol: after connecting, the client sends {"type": "auth", "token": "<JWT>"}
    as its first message (keeps the token out of URLs and access logs). The server
    replies {"type": "ready"} and then pushes events such as
    {"type": "analytics.updated", "module": "inventory", ...}.
    """
    await websocket.accept()

    try:
        first = await asyncio.wait_for(websocket.receive_json(), timeout=AUTH_TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError):
        await websocket.close(code=1008)
        return

    token = first.get("token") if isinstance(first, dict) and first.get("type") == "auth" else None
    permissions = await asyncio.to_thread(_authenticate, token)
    if permissions is None:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await manager.register(websocket, permissions)
    await websocket.send_json({"type": "ready"})

    try:
        while True:
            # Client may send pings; content is ignored.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unexpected WebSocket error")
    finally:
        await manager.disconnect(websocket)
