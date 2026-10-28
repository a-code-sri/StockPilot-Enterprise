from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.outbox.models import AnalyticsOutbox


PENDING = "pending"
PROCESSING = "processing"
DONE = "done"
FAILED = "failed"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_event(
    db: Session,
    *,
    module: str,
    event_type: str,
    payload: dict[str, Any],
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
) -> AnalyticsOutbox:
    """
    Add an outbox event to the current DB transaction.

    IMPORTANT:
    - This function does NOT commit.
    - Caller should commit/rollback together with the business write.
    """
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
    db.flush()  # assigns PK id without committing
    return row


def fetch_and_lock_batch(db: Session, *, limit: int = 100) -> list[AnalyticsOutbox]:
    """
    Fetch a batch of available outbox rows and lock them so only one worker processes them.

    Uses SELECT ... FOR UPDATE SKIP LOCKED to support multiple workers safely.
    """
    now = utcnow()

    rows = (
        db.query(AnalyticsOutbox)
        .filter(
            AnalyticsOutbox.status.in_([PENDING, FAILED]),
            AnalyticsOutbox.available_at <= now,
        )
        .order_by(AnalyticsOutbox.created_at.asc(), AnalyticsOutbox.id.asc())
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )

    if not rows:
        return []

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


def mark_failed(
    db: Session,
    row: AnalyticsOutbox,
    *,
    error_message: str,
    backoff_seconds: int = 10,
) -> None:
    """
    Mark the row failed and schedule it for retry after backoff_seconds.
    """
    now = utcnow()
    row.status = FAILED
    row.attempts = (row.attempts or 0) + 1
    row.last_error = error_message[:10000]  # prevent huge logs
    row.available_at = now + timedelta(seconds=backoff_seconds)
    row.updated_at = now
    db.flush()