import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.modules.accounts.infrastructure.projections import (
    AccountsDailyTotals,
    AccountsDailyCategoryTotals,
)

logger = logging.getLogger(__name__)


def _parse_day(payload: dict[str, Any]) -> date:
    raw = payload.get("date")
    if not raw:
        return datetime.utcnow().date()

    if isinstance(raw, str):
        s = raw.strip()
        # handle ISO strings that end with 'Z'
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return datetime.utcnow().date()

    if isinstance(raw, datetime):
        return raw.date()

    return datetime.utcnow().date()


def _as_decimal(value: Any) -> Decimal:
    # robust conversion from float/str/int to Decimal
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _apply_transaction_delta(
    db: Session,
    *,
    day: date,
    transaction_type: str,
    category: str,
    amount: Decimal,
) -> None:
    """
    Incrementally update projections using UPSERT.
    `amount` can be positive (create) or negative (delete).
    """
    ttype = (transaction_type or "").lower()
    category = category or "Uncategorized"

    income_delta = amount if ttype == "credit" else Decimal("0")
    expense_delta = amount if ttype == "debit" else Decimal("0")

    # 1) Daily totals upsert: add deltas to existing row
    stmt_totals = pg_insert(AccountsDailyTotals).values(
        day=day,
        income=income_delta,
        expenses=expense_delta,
    )
    stmt_totals = stmt_totals.on_conflict_do_update(
        index_elements=[AccountsDailyTotals.day],
        set_={
            "income": AccountsDailyTotals.income + stmt_totals.excluded.income,
            "expenses": AccountsDailyTotals.expenses + stmt_totals.excluded.expenses,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt_totals)

    # 2) Daily category totals upsert
    stmt_cat = pg_insert(AccountsDailyCategoryTotals).values(
        day=day,
        category=category,
        transaction_type=ttype,
        amount=amount,
    )
    stmt_cat = stmt_cat.on_conflict_do_update(
        constraint="pk_accounts_daily_category_totals",
        set_={
            "amount": AccountsDailyCategoryTotals.amount + stmt_cat.excluded.amount,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt_cat)


def handle_transaction_created(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    day = _parse_day(payload)
    amount = _as_decimal(payload.get("amount"))
    ttype = payload.get("transaction_type") or payload.get("type") or ""
    category = payload.get("category") or "Uncategorized"

    logger.info(
        "accounts analytics: transaction_created outbox_id=%s tx_id=%s",
        outbox_id,
        payload.get("transaction_id"),
    )

    _apply_transaction_delta(
        db,
        day=day,
        transaction_type=str(ttype),
        category=str(category),
        amount=amount,  # positive
    )


def handle_transaction_deleted(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    day = _parse_day(payload)
    amount = _as_decimal(payload.get("amount"))
    ttype = payload.get("transaction_type") or payload.get("type") or ""
    category = payload.get("category") or "Uncategorized"

    logger.info(
        "accounts analytics: transaction_deleted outbox_id=%s tx_id=%s",
        outbox_id,
        payload.get("transaction_id"),
    )

    _apply_transaction_delta(
        db,
        day=day,
        transaction_type=str(ttype),
        category=str(category),
        amount=-amount,  # negative delta to undo
    )


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("accounts analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)