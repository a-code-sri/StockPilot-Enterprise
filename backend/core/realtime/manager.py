from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from backend.core.rbac.permissions import MODULE_READ_PERMISSION

logger = logging.getLogger("realtime")


class ConnectionManager:
    """
    Tracks authenticated WebSocket connections and broadcasts realtime events.

    Each connection remembers the user's permissions at connect time; an event
    tagged with a module is only delivered to users who can read that module.
    """

    def __init__(self) -> None:
        self._connections: dict[WebSocket, frozenset[str]] = {}
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket, permissions: set[str]) -> None:
        async with self._lock:
            self._connections[websocket] = frozenset(permissions)
        logger.info("WebSocket connected. Active connections: %s", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)
        logger.info("WebSocket disconnected. Active connections: %s", len(self._connections))

    @staticmethod
    def _can_receive(permissions: frozenset[str], message: dict[str, Any]) -> bool:
        required = MODULE_READ_PERMISSION.get(str(message.get("module") or ""))
        return required is None or required in permissions

    async def broadcast(self, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = [ws for ws, perms in self._connections.items() if self._can_receive(perms, message)]

        dead: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)

        if dead:
            async with self._lock:
                for websocket in dead:
                    self._connections.pop(websocket, None)

        logger.debug("Broadcast realtime event to %s client(s)", len(targets) - len(dead))

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
