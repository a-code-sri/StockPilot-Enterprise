from __future__ import annotations

import asyncio
import json
import logging
import select
import threading
from typing import Any

import psycopg2
import psycopg2.extensions

from backend.core.config import get_settings

logger = logging.getLogger("realtime.listener")

RECONNECT_MAX_SECONDS = 30


class RealtimeListener:
    """
    PostgreSQL LISTEN/NOTIFY -> WebSocket bridge.

    Runs a blocking LISTEN loop in a background thread and hands each event to the
    ConnectionManager on FastAPI's event loop. Reconnects with exponential backoff
    if the database connection drops, so realtime updates recover by themselves.
    """

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connection = None
        settings = get_settings()
        self._dsn = settings.listen_database_url
        self._channel = settings.REALTIME_LISTEN_CHANNEL

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self.is_running:
            return
        self._loop = loop
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_forever, name="realtime-listener", daemon=True)
        self._thread.start()
        logger.info("Realtime listener started on channel '%s'", self._channel)

    def stop(self) -> None:
        self._stop_event.set()
        conn = self._connection
        if conn is not None:
            try:
                conn.close()  # wakes select()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        self._connection = None
        logger.info("Realtime listener stopped")

    # ------------------------------------------------------------------

    def _run_forever(self) -> None:
        delay = 1.0
        while not self._stop_event.is_set():
            try:
                self._listen_once()
                delay = 1.0
            except Exception:
                if self._stop_event.is_set():
                    break
                logger.exception("Realtime listener connection failed; retrying in %.0fs", delay)
            finally:
                self._close_connection()

            if self._stop_event.wait(delay):
                break
            delay = min(delay * 2, RECONNECT_MAX_SECONDS)

    def _close_connection(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connection = None

    def _listen_once(self) -> None:
        self._connection = psycopg2.connect(self._dsn)
        self._connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with self._connection.cursor() as cur:
            # Channel names are identifiers; quote to be safe with config-provided values.
            cur.execute(f'LISTEN "{self._channel}";')
        logger.info("LISTENing on PostgreSQL channel '%s'", self._channel)

        while not self._stop_event.is_set():
            readable, _, _ = select.select([self._connection], [], [], 1.0)
            if not readable:
                continue
            self._connection.poll()
            while self._connection.notifies:
                self._handle_notification(self._connection.notifies.pop(0).payload)

    def _handle_notification(self, payload: str) -> None:
        try:
            event: dict[str, Any] = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Ignoring invalid realtime event payload: %r", payload)
            return

        if self._loop is None:
            return

        from backend.core.realtime.manager import manager

        future = asyncio.run_coroutine_threadsafe(manager.broadcast(event), self._loop)

        def _consume_result(fut) -> None:
            try:
                fut.result()
            except Exception:
                logger.exception("Failed to broadcast realtime event")

        future.add_done_callback(_consume_result)


realtime_listener = RealtimeListener()
