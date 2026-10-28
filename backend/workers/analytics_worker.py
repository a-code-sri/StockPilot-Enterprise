from __future__ import annotations

import json
import logging
import os
import psycopg2
import select
import time
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session

load_dotenv()

from backend.core.database.session import SessionLocal, engine
from backend.outbox.models import AnalyticsOutbox
from backend.outbox.repository import (
    fetch_and_lock_batch,
    mark_done,
    mark_failed,
)
from backend.workers.dispatcher import HandlerNotFound, dispatch


logger = logging.getLogger("analytics_worker")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())


LISTEN_CHANNEL = os.getenv("OUTBOX_LISTEN_CHANNEL", "analytics_outbox")
BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", "50"))
POLL_TIMEOUT_SECONDS = int(os.getenv("OUTBOX_POLL_TIMEOUT", "10"))
STALE_LOCK_SECONDS = int(os.getenv("STALE_LOCK_SECONDS", "300"))
MAX_BACKOFF_SECONDS = int(os.getenv("OUTBOX_MAX_BACKOFF_SECONDS", "300"))

REALTIME_CHANNEL = os.getenv(
    "REALTIME_LISTEN_CHANNEL",
    "realtime_events",
)

DIRECT_DATABASE_URL = os.getenv("DIRECT_DATABASE_URL")

if not DIRECT_DATABASE_URL:
    raise RuntimeError(
        "DIRECT_DATABASE_URL is required for analytics worker LISTEN/NOTIFY"
    )


def publish_realtime_event(
    db: Session,
    *,
    module: str,
    event_type: str,
    outbox_id: int,
) -> None:

    payload = json.dumps(
        {
            "type": "analytics.updated",
            "module": module,
            "event_type": event_type,
            "outbox_id": outbox_id,
        }
    )

    print(
        f"ABOUT TO PUBLISH REALTIME: "
        f"channel={REALTIME_CHANNEL} payload={payload}"
    )

    db.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {
            "channel": REALTIME_CHANNEL,
            "payload": payload,
        },
    )

    print(
        f"PG_NOTIFY EXECUTED: outbox_id={outbox_id}"
    )


def _backoff_seconds(attempts: int) -> int:
    # simple exponential backoff: 10, 20, 40, 80 ... capped
    base = 10 * (2 ** max(0, attempts))
    return min(base, MAX_BACKOFF_SECONDS)


def reclaim_stale_processing_rows(db: Session) -> int:
    """
    If a worker crashes mid-processing, some rows might remain stuck in 'processing'.
    This reclaims them so they can be retried.
    """
    from datetime import datetime, timezone, timedelta

    threshold = datetime.now(timezone.utc) - timedelta(
        seconds=STALE_LOCK_SECONDS
    )

    rows = (
        db.query(AnalyticsOutbox)
        .filter(
            AnalyticsOutbox.status == "processing",
            AnalyticsOutbox.locked_at.isnot(None),
            AnalyticsOutbox.locked_at < threshold,
        )
        .all()
    )

    for r in rows:
        r.status = "failed"
        r.last_error = (
            (r.last_error or "")
            + "\n[reclaimed stale processing lock]"
        )
        r.available_at = datetime.now(timezone.utc)

    if rows:
        db.flush()

    return len(rows)


def process_pending_once() -> int:
    """
    Processes available outbox rows until none remain (in small batches).
    Returns number of rows successfully marked done in this run.
    """
    done_count = 0

    db = SessionLocal()

    try:
        reclaimed = reclaim_stale_processing_rows(db)

        if reclaimed:
            db.commit()
            logger.warning(
                "Reclaimed %s stale processing outbox rows",
                reclaimed,
            )

        while True:
            locked_rows = fetch_and_lock_batch(
                db,
                limit=BATCH_SIZE,
            )

            if not locked_rows:
                db.commit()
                break

            # Snapshot needed fields before commit
            # (avoid expiration issues)
            events: list[dict[str, Any]] = [
                {
                    "id": r.id,
                    "module": r.module,
                    "event_type": r.event_type,
                    "payload": r.payload,
                    "attempts": int(r.attempts or 0),
                }
                for r in locked_rows
            ]

            # Persist "processing" status quickly
            db.commit()

            for ev in events:
                outbox_id = ev["id"]
                module = ev["module"]
                event_type = ev["event_type"]
                payload = ev["payload"]
                attempts = ev["attempts"]

                try:
                    dispatch(
                        db=db,
                        module=module,
                        event_type=event_type,
                        payload=payload,
                        outbox_id=outbox_id,
                    )

                    row = db.get(
                        AnalyticsOutbox,
                        outbox_id,
                    )

                    if row:
                        mark_done(db, row)

                    publish_realtime_event(
                        db,
                        module=module,
                        event_type=event_type,
                        outbox_id=outbox_id,
                    )

                    db.commit()
                    done_count += 1

                except HandlerNotFound as e:
                    db.rollback()

                    row = db.get(
                        AnalyticsOutbox,
                        outbox_id,
                    )

                    if row:
                        mark_failed(
                            db,
                            row,
                            error_message=f"HandlerNotFound: {e}",
                            backoff_seconds=_backoff_seconds(
                                attempts
                            ),
                        )
                        db.commit()

                    logger.error(
                        "Outbox %s handler not found: %s",
                        outbox_id,
                        e,
                    )

                except Exception as e:
                    db.rollback()

                    row = db.get(
                        AnalyticsOutbox,
                        outbox_id,
                    )

                    if row:
                        mark_failed(
                            db,
                            row,
                            error_message=str(e),
                            backoff_seconds=_backoff_seconds(
                                attempts
                            ),
                        )
                        db.commit()

                    logger.exception(
                        "Outbox %s processing failed",
                        outbox_id,
                    )

    finally:
        db.close()

    return done_count


def listen_and_process_forever() -> None:
    """
    LISTEN/NOTIFY driven loop (fast reaction), with periodic sweeps for safety.

    The LISTEN connection intentionally uses the Neon direct connection,
    while normal SQLAlchemy work continues to use SessionLocal().
    """

    # Persistent LISTEN connection must use the direct Neon connection.
    raw_conn = psycopg2.connect(DIRECT_DATABASE_URL)

    try:
        if engine.dialect.name != "postgresql":
            raise RuntimeError(
                f"analytics_worker requires PostgreSQL for LISTEN/NOTIFY, "
                f"but current dialect is '{engine.dialect.name}'. "
                f"Set DATABASE_URL to a postgres URL."
            )

        # Ensure NOTIFY events are delivered without needing explicit commits.
        raw_conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
        )

        cur = raw_conn.cursor()
        cur.execute(f"LISTEN {LISTEN_CHANNEL};")

        print(
            f"Worker LISTENing on channel '{LISTEN_CHANNEL}'"
        )

        # Initial sweep on startup
        n = process_pending_once()

        if n:
            print(
                f"Processed {n} outbox event(s) on startup"
            )

        while True:
            # Wait for notifications or timeout
            rlist, _, _ = select.select(
                [raw_conn],
                [],
                [],
                POLL_TIMEOUT_SECONDS,
            )

            if rlist:
                raw_conn.poll()

                # Drain notifications quickly
                notify_count = 0

                while raw_conn.notifies:
                    raw_conn.notifies.pop(0)
                    notify_count += 1

                logger.debug(
                    "Received %s NOTIFY message(s)",
                    notify_count,
                )

            # Whether notified or timed out, run a sweep
            processed = process_pending_once()

            if processed:
                print(
                    f"Processed {processed} outbox event(s)"
                )

            # Tiny sleep prevents tight loop if DB is very fast and empty
            time.sleep(0.2)

    finally:
        try:
            raw_conn.close()
        except Exception:
            pass


def main() -> None:
    listen_and_process_forever()


if __name__ == "__main__":
    main()