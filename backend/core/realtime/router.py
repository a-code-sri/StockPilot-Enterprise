from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.auth.jwt_handler import decode_access_token
from backend.core.auth.models import User
from backend.core.database.session import SessionLocal
from backend.core.realtime.manager import manager

logger = logging.getLogger("realtime")

router = APIRouter()


def authenticate_websocket(token: str | None) -> User | None:
    """
    Authenticate a WebSocket connection using the same JWT mechanism
    used by the REST API.
    """

    if not token:
        return None

    payload = decode_access_token(token)

    if payload is None:
        return None

    username = payload.get("sub")

    if not username:
        return None

    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        return user

    finally:
        db.close()


@router.websocket("/ws/realtime")
async def realtime_websocket(
    websocket: WebSocket,
) -> None:
    """
    Authenticated WebSocket endpoint for realtime application events.

    Current authentication mechanism:
        /ws/realtime?token=<JWT>

    The WebSocket is notification-only for now.
    """

    token = websocket.query_params.get("token")

    user = authenticate_websocket(token)

    if user is None:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket)

    try:
        while True:
            # Keep the connection alive and allow the client to send
            # lightweight heartbeat/ping messages later.
            await websocket.receive_text()

    except WebSocketDisconnect:
        await manager.disconnect(websocket)

    except Exception:
        logger.exception("Unexpected WebSocket error")
        await manager.disconnect(websocket)