"""Outbox handlers that maintain the accounts projections (UTC-day buckets)."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.core.time import parse_iso_datetime, utctoday
from backend.modules.accounts.infrastructure.projections import AccountsDailyCategoryTotals, AccountsDailyTotals

logger = logging.getLogger(__name__)


def _parse_day(payload: dict[str, Any]) -> date:
    dt = parse_iso_datetime(payload.get("date"))
    return dt.date() if dt else utctoday()


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def apply_transaction_delta(db: Session, *, day: date, transaction_type: str, category: str, amount: Decimal) -> None:
    """UPSERT deltas into the projections. `amount` is negative to undo a transaction."""
    ttype = (transaction_type or "").lower()
    category = category or "Uncategorized"

    income_delta = amount if ttype == "credit" else Decimal("0")
    expense_delta = amount if ttype == "debit" else Decimal("0")

    stmt = pg_insert(AccountsDailyTotals).values(day=day, income=income_delta, expenses=expense_delta)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AccountsDailyTotals.day],
        set_={
            "income": AccountsDailyTotals.income + stmt.excluded.income,
            "expenses": AccountsDailyTotals.expenses + stmt.excluded.expenses,
            "updated_at": func.now(),
        },
    )
    db.execute(stmt)

    stmt_cat = pg_insert(AccountsDailyCategoryTotals).values(
        day=day, category=category, transaction_type=ttype, amount=amount
    )
    stmt_cat = stmt_cat.on_conflict_do_update(
        constraint="pk_accounts_daily_category_totals",
        set_={"amount": AccountsDailyCategoryTotals.amount + stmt_cat.excluded.amount, "updated_at": func.now()},
    )
    db.execute(stmt_cat)


def _apply(db: Session, payload: dict[str, Any], sign: int) -> None:
    apply_transaction_delta(
        db,
        day=_parse_day(payload),
        transaction_type=str(payload.get("transaction_type") or payload.get("type") or ""),
        category=str(payload.get("category") or "Uncategorized"),
        amount=_as_decimal(payload.get("amount")) * sign,
    )


def handle_transaction_created(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    logger.info("accounts: transaction_created outbox_id=%s tx_id=%s", outbox_id, payload.get("transaction_id"))
    _apply(db, payload, +1)


def handle_transaction_deleted(db: Session, payload: dict[str, Any], outbox_id: int) -> None:
    logger.info("accounts: transaction_deleted outbox_id=%s tx_id=%s", outbox_id, payload.get("transaction_id"))
    _apply(db, payload, -1)


def handle_event(db: Session, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    logger.warning("accounts analytics: unhandled event '%s' (outbox_id=%s)", event_type, outbox_id)
