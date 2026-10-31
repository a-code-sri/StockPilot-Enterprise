"""
Analytics outbox worker.

    python -m backend.workers.analytics_worker

Waits for NOTIFY on the outbox channel (with a periodic sweep as a safety net),
claims due events, runs the matching projection handler, and publishes a realtime
notification for each processed event. Reconnects automatically if the database
connection drops.
"""

from __future__ import annotations

import json
import logging
import select
import time
from datetime import timedelta
from typing import Any

import psycopg2
import psycopg2.extensions
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.database.registry import import_all_models
from backend.core.database.session import SessionLocal, engine
from backend.core.time import utcnow
from backend.outbox import repository as outbox
from backend.outbox.models import AnalyticsOutbox
from backend.workers.dispatcher import HandlerNotFound, dispatch

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("analytics_worker")

PRUNE_INTERVAL_SECONDS = 3600
RECONNECT_MAX_SECONDS = 30


def publish_realtime_event(db: Session, *, module: str, event_type: str, outbox_id: int) -> None:
    payload = json.dumps(
        {"type": "analytics.updated", "module": module, "event_type": event_type, "outbox_id": outbox_id}
    )
    # Delivered on commit, so clients never refetch before the projection is visible.
    db.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": settings.REALTIME_LISTEN_CHANNEL, "payload": payload},
    )


def reclaim_stale_processing_rows(db: Session) -> int:
    """Rows left in 'processing' by a crashed worker become retryable again."""
    threshold = utcnow() - timedelta(seconds=settings.STALE_LOCK_SECONDS)
    rows = (
        db.query(AnalyticsOutbox)
        .filter(
            AnalyticsOutbox.status == outbox.PROCESSING,
            AnalyticsOutbox.locked_at.isnot(None),
            AnalyticsOutbox.locked_at < threshold,
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    for r in rows:
        r.status = outbox.FAILED
        r.last_error = ((r.last_error or "") + "\n[reclaimed stale processing lock]").strip()
        r.available_at = utcnow()
    db.flush()
    return len(rows)


def _process_event(db: Session, ev: dict[str, Any]) -> bool:
    """Process one claimed event in its own transaction. Returns True on success."""
    outbox_id = ev["id"]
    try:
        dispatch(db=db, module=ev["module"], event_type=ev["event_type"], payload=ev["payload"], outbox_id=outbox_id)
        row = db.get(AnalyticsOutbox, outbox_id)
        if row:
            outbox.mark_done(db, row)
        publish_realtime_event(db, module=ev["module"], event_type=ev["event_type"], outbox_id=outbox_id)
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        permanent = isinstance(exc, HandlerNotFound)
        row = db.get(AnalyticsOutbox, outbox_id)
        if row:
            status = outbox.mark_failed(
                db,
                row,
                error_message=f"{type(exc).__name__}: {exc}",
                max_attempts=settings.OUTBOX_MAX_ATTEMPTS,
                max_backoff=settings.OUTBOX_MAX_BACKOFF_SECONDS,
                permanent=permanent,
            )
            db.commit()
            log = logger.error if status == outbox.DEAD else logger.warning
            log("Outbox %s (%s.%s) failed -> %s: %s", outbox_id, ev["module"], ev["event_type"], status, exc)
        if not permanent:
            logger.debug("Traceback for outbox %s", outbox_id, exc_info=True)
        return False


def process_pending_once() -> int:
    """Process due rows in batches until none remain. Returns number succeeded."""
    done_count = 0
    db = SessionLocal()
    try:
        reclaimed = reclaim_stale_processing_rows(db)
        db.commit()
        if reclaimed:
            logger.warning("Reclaimed %s stale processing outbox rows", reclaimed)

        while True:
            locked = outbox.fetch_and_lock_batch(db, limit=settings.OUTBOX_BATCH_SIZE)
            events = [
                {"id": r.id, "module": r.module, "event_type": r.event_type, "payload": r.payload}
                for r in locked
            ]
            db.commit()  # persist 'processing' quickly
            if not events:
                break
            for ev in events:
                if _process_event(db, ev):
                    done_count += 1
    finally:
        db.close()
    return done_count


def prune_old_events() -> None:
    db = SessionLocal()
    try:
        deleted = outbox.prune_done(db, older_than_days=settings.OUTBOX_RETENTION_DAYS)
        db.commit()
        if deleted:
            logger.info("Pruned %s processed outbox rows", deleted)
    finally:
        db.close()


def _listen_loop() -> None:
    raw_conn = psycopg2.connect(settings.listen_database_url)
    try:
        raw_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with raw_conn.cursor() as cur:
            cur.execute(f'LISTEN "{settings.OUTBOX_LISTEN_CHANNEL}";')
        logger.info("Worker LISTENing on channel '%s'", settings.OUTBOX_LISTEN_CHANNEL)

        n = process_pending_once()
        if n:
            logger.info("Processed %s outbox event(s) on startup", n)

        last_prune = 0.0
        while True:
            readable, _, _ = select.select([raw_conn], [], [], settings.OUTBOX_POLL_TIMEOUT)
            if readable:
                raw_conn.poll()
                raw_conn.notifies.clear()

            processed = process_pending_once()
            if processed:
                logger.info("Processed %s outbox event(s)", processed)

            if time.monotonic() - last_prune > PRUNE_INTERVAL_SECONDS:
                prune_old_events()
                last_prune = time.monotonic()
    finally:
        try:
            raw_conn.close()
        except Exception:
            pass


def listen_and_process_forever() -> None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("analytics_worker requires PostgreSQL (LISTEN/NOTIFY).")

    delay = 1.0
    while True:
        try:
            _listen_loop()
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("Worker loop crashed; reconnecting in %.0fs", delay)
            time.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_SECONDS)
        else:
            delay = 1.0


def main() -> None:
    import_all_models()
    try:
        listen_and_process_forever()
    except KeyboardInterrupt:
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()
