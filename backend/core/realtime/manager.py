from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("realtime")


class ConnectionManager:
    """
    Maintains active WebSocket connections and broadcasts realtime events.

    This class deliberately contains no business or analytics logic.
    It only manages connected clients and sends messages to them.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

        async with self._lock:
            self._connections.add(websocket)

        logger.info(
            "WebSocket connected. Active connections: %s",
            len(self._connections),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

        logger.info(
            "WebSocket disconnected. Active connections: %s",
            len(self._connections),
        )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Broadcast a JSON message to all currently connected clients.

        Dead connections are removed automatically.
        """
        async with self._lock:
            connections = list(self._connections)

        if not connections:
            return

        dead_connections: list[WebSocket] = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.append(websocket)

        if dead_connections:
            async with self._lock:
                for websocket in dead_connections:
                    self._connections.discard(websocket)

        logger.debug(
            "Broadcast realtime event to %s client(s)",
            len(connections) - len(dead_connections),
        )

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()