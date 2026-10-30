from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import delete, insert
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from backend.core.time import utcnow
from backend.outbox.models import AnalyticsOutbox

PENDING = "pending"
PROCESSING = "processing"
DONE = "done"
FAILED = "failed"   # retryable after available_at
DEAD = "dead"       # gave up; inspect last_error, fix, then reset status to 'pending'


def emit_event(
    connection: Connection,
    *,
    module: str,
    event_type: str,
    payload: dict[str, Any],
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
) -> None:
    """
    Insert an outbox row on a Core connection. Used from ORM mapper events
    (after_insert/after_update/after_delete), which run inside the business
    transaction, so the event commits or rolls back together with the write.
    """
    now = utcnow()
    connection.execute(
        insert(AnalyticsOutbox).values(
            module=module,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status=PENDING,
            available_at=now,
        )
    )


def enqueue_event(
    db: Session,
    *,
    module: str,
    event_type: str,
    payload: dict[str, Any],
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
) -> AnalyticsOutbox:
    """Add an outbox event to the current ORM transaction. Does NOT commit."""
    row = AnalyticsOutbox(
        module=module,
        event_type=event_type,
        payload=payload,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        status=PENDING,
        available_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def fetch_and_lock_batch(db: Session, *, limit: int = 100) -> list[AnalyticsOutbox]:
    """
    Claim a batch of due rows with SELECT ... FOR UPDATE SKIP LOCKED so several
    workers can run safely.
    """
    now = utcnow()
    rows = (
        db.query(AnalyticsOutbox)
        .filter(AnalyticsOutbox.status.in_([PENDING, FAILED]), AnalyticsOutbox.available_at <= now)
        .order_by(AnalyticsOutbox.created_at.asc(), AnalyticsOutbox.id.asc())
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )
    for r in rows:
        r.status = PROCESSING
        r.locked_at = now
        r.updated_at = now
    db.flush()
    return rows


def mark_done(db: Session, row: AnalyticsOutbox) -> None:
    now = utcnow()
    row.status = DONE
    row.processed_at = now
    row.last_error = None
    row.updated_at = now
    db.flush()


def backoff_seconds(attempts: int, *, base: int = 10, cap: int = 300) -> int:
    """Exponential backoff: 10, 20, 40, ... capped. `attempts` = failures so far."""
    return min(base * (2 ** max(0, attempts)), cap)


def mark_failed(
    db: Session,
    row: AnalyticsOutbox,
    *,
    error_message: str,
    max_attempts: int,
    max_backoff: int = 300,
    permanent: bool = False,
) -> str:
    """
    Record a failure. Retries with backoff until `max_attempts`, then marks the row
    DEAD so a poison event cannot loop forever. Returns the new status.
    """
    now = utcnow()
    previous = row.attempts or 0
    row.attempts = previous + 1
    row.last_error = error_message[:10000]
    row.updated_at = now
    row.locked_at = None

    if permanent or row.attempts >= max_attempts:
        row.status = DEAD
    else:
        row.status = FAILED
        row.available_at = now + timedelta(seconds=backoff_seconds(previous, cap=max_backoff))
    db.flush()
    return row.status


def prune_done(db: Session, *, older_than_days: int) -> int:
    """Delete processed rows past the retention window. Returns rows deleted."""
    cutoff = utcnow() - timedelta(days=older_than_days)
    result = db.execute(
        delete(AnalyticsOutbox).where(AnalyticsOutbox.status == DONE, AnalyticsOutbox.processed_at < cutoff)
    )
    return result.rowcount or 0
