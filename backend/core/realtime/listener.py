from __future__ import annotations

import asyncio
import json
import logging
import os
import select
import threading
from typing import Any

import psycopg2

from backend.core.database.session import DATABASE_URL
from backend.core.database.session import DIRECT_DATABASE_URL
DIRECT_DATABASE_URL = os.getenv("DIRECT_DATABASE_URL")
logger = logging.getLogger("realtime_listener")


REALTIME_LISTEN_CHANNEL = os.getenv(
    "REALTIME_LISTEN_CHANNEL",
    "realtime_events",
)


class RealtimeListener:
    """
    PostgreSQL LISTEN/NOTIFY listener.

    Runs the blocking PostgreSQL listener in a background thread and
    forwards received events into FastAPI's asyncio event loop.
    """

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connection = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._loop = loop
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="realtime-listener",
            daemon=True,
        )

        self._thread.start()

        print(
            "Realtime listener started on channel '%s'",
            REALTIME_LISTEN_CHANNEL,
        )

    def stop(self) -> None:
        self._stop_event.set()

        # Closing the PostgreSQL connection wakes select()
        # so the listener thread can exit promptly.
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        self._thread = None
        self._connection = None

        logger.info("Realtime listener stopped")

    def _run(self) -> None:
        try:
            database_url = DATABASE_URL.replace(
                "postgresql+psycopg2://",
                "postgresql://",
            )

            self._connection = psycopg2.connect(database_url)
            self._connection = psycopg2.connect(DIRECT_DATABASE_URL)
            self._connection.set_isolation_level(
                psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
            )

            cursor = self._connection.cursor()
            cursor.execute(
                f"LISTEN {REALTIME_LISTEN_CHANNEL};"
            )

            print(
                "LISTENing on PostgreSQL channel '%s'",
                REALTIME_LISTEN_CHANNEL,
            )

            while not self._stop_event.is_set():
                try:
                    readable, _, _ = select.select(
                        [self._connection],
                        [],
                        [],
                        1.0,
                    )
                except (ValueError, OSError):
                    break

                if not readable:
                    continue

                try:
                    self._connection.poll()
                except Exception:
                    if not self._stop_event.is_set():
                        logger.exception(
                            "Failed to poll realtime PostgreSQL connection"
                        )
                    break

                while self._connection.notifies:
                    notification = self._connection.notifies.pop(0)

                    self._handle_notification(
                        notification.payload
                    )

        except Exception:
            if not self._stop_event.is_set():
                logger.exception(
                    "Realtime PostgreSQL listener crashed"
                )

        finally:
            if self._connection is not None:
                try:
                    self._connection.close()
                except Exception:
                    pass

            self._connection = None

    def _handle_notification(self, payload: str) -> None:
        print("REALTIME PostgreSQL notification received: %s", payload)
        try:
            event: dict[str, Any] = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning(
                "Ignoring invalid realtime event payload: %r",
                payload,
            )
            return

        if self._loop is None:
            return

        from backend.core.realtime.manager import manager

        future = asyncio.run_coroutine_threadsafe(
            manager.broadcast(event),
            self._loop,
        )

        def _consume_result(fut) -> None:
            try:
                fut.result()
            except Exception:
                logger.exception(
                    "Failed to broadcast realtime event"
                )

        future.add_done_callback(_consume_result)


realtime_listener = RealtimeListener()