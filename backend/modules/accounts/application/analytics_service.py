"""
Read-side analytics for accounts. Totals come from the projections maintained by
the worker; rankings and anomalies read the transactions table (indexed by date).
"""

from __future__ import annotations

import math
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.time import utcnow, utctoday
from backend.modules.accounts.application.anomalies import detect_transaction_anomalies
from backend.modules.accounts.infrastructure.models import TransactionModel, TransactionTypeEnum
from backend.modules.accounts.infrastructure.projections import AccountsDailyCategoryTotals, AccountsDailyTotals


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def liquidity_score(*, current_balance: float, total_credit: float, total_debit: float, days: int) -> dict:
    """
    Explainable 0-100 score:
      - up to 60 points for net cash flow relative to spending (tanh-squashed)
      - up to 40 points for runway (days current balance covers average spending; full at 60 days)
    """
    net = total_credit - total_debit
    avg_daily_debit = total_debit / max(days, 1)
    buffer_days = None if avg_daily_debit <= 0 else current_balance / avg_daily_debit

    net_score = 30.0 + 30.0 * math.tanh(net / max(total_debit, 1.0))
    buffer_score = 40.0 if buffer_days is None else 40.0 * _clamp(buffer_days / 60.0, 0.0, 1.0)

    return {
        "days": days,
        "score": round(_clamp(net_score + buffer_score, 0.0, 100.0), 2),
        "current_balance": round(current_balance, 2),
        "net": round(net, 2),
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "avg_daily_debit": round(avg_daily_debit, 2),
        "buffer_days": None if buffer_days is None else round(buffer_days, 2),
    }


class AccountsAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _window_start(self, days: int):
        return utctoday() - timedelta(days=days - 1)

    def totals(self, days: int | None) -> tuple[float, float]:
        q = self.db.query(
            func.coalesce(func.sum(AccountsDailyTotals.income), 0),
            func.coalesce(func.sum(AccountsDailyTotals.expenses), 0),
        )
        if days is not None:
            q = q.filter(AccountsDailyTotals.day >= self._window_start(days))
        income, expenses = q.one()
        return float(Decimal(income)), float(Decimal(expenses))

    def distribution_by_category(self, days: int, transaction_type: str) -> list[dict]:
        rows = (
            self.db.query(AccountsDailyCategoryTotals.category, func.sum(AccountsDailyCategoryTotals.amount))
            .filter(
                AccountsDailyCategoryTotals.day >= self._window_start(days),
                AccountsDailyCategoryTotals.transaction_type == transaction_type,
            )
            .group_by(AccountsDailyCategoryTotals.category)
            .having(func.sum(AccountsDailyCategoryTotals.amount) > 0)
            .order_by(func.sum(AccountsDailyCategoryTotals.amount).desc())
            .all()
        )
        return [{"category": c, "amount": float(a)} for c, a in rows]

    def _top_counterparties(self, days: int, ttype: TransactionTypeEnum, top_n: int):
        since = utcnow() - timedelta(days=days)
        return (
            self.db.query(TransactionModel.source_target, func.sum(TransactionModel.amount))
            .filter(TransactionModel.transaction_type == ttype, TransactionModel.date >= since)
            .group_by(TransactionModel.source_target)
            .order_by(func.sum(TransactionModel.amount).desc())
            .limit(top_n)
            .all()
        )

    def liquidity(self, days: int) -> dict:
        all_income, all_expenses = self.totals(None)
        income, expenses = self.totals(days)
        return liquidity_score(
            current_balance=all_income - all_expenses, total_credit=income, total_debit=expenses, days=days
        )

    def overview(self, days: int, top_n: int) -> dict:
        income, expenses = self.totals(days)
        return {
            "window_days": days,
            "income_vs_expenses": {"income": income, "expenses": expenses, "net": round(income - expenses, 2)},
            "income_by_category": self.distribution_by_category(days, "credit"),
            "expense_by_category": self.distribution_by_category(days, "debit"),
            "rankings": {
                "top_income_sources": [
                    {"source": s, "amount": float(a)}
                    for s, a in self._top_counterparties(days, TransactionTypeEnum.credit, top_n)
                ],
                "top_expense_targets": [
                    {"target": s, "amount": float(a)}
                    for s, a in self._top_counterparties(days, TransactionTypeEnum.debit, top_n)
                ],
            },
            "liquidity": {"score_30d": self.liquidity(30), "score_365d": self.liquidity(365)},
        }

    def series(self, days: int) -> dict:
        start, end = self._window_start(days), utctoday()
        rows = {
            r.day: r
            for r in self.db.query(AccountsDailyTotals)
            .filter(AccountsDailyTotals.day >= start, AccountsDailyTotals.day <= end)
            .all()
        }
        series = []
        for i in range(days):
            d = start + timedelta(days=i)
            r = rows.get(d)
            income = float(r.income) if r else 0.0
            expenses = float(r.expenses) if r else 0.0
            series.append({"day": d.isoformat(), "income": income, "expenses": expenses, "net": income - expenses})
        return {"days": days, "range": {"start": start.isoformat(), "end": end.isoformat()}, "series": series}

    def anomalies(self, days: int, limit: int) -> dict:
        since = utcnow() - timedelta(days=days)
        rows = (
            self.db.query(TransactionModel)
            .filter(TransactionModel.date >= since)
            .order_by(TransactionModel.date.desc())
            .limit(20000)
            .all()
        )
        txs = [
            {
                "id": r.id,
                "amount": r.amount,
                "transaction_type": r.transaction_type.value,
                "category": r.category,
                "source_target": r.source_target,
                "date": r.date.isoformat(),
            }
            for r in rows
        ]
        found = detect_transaction_anomalies(txs)
        return {"window_days": days, "scanned": len(txs), "anomalies": found[:limit]}
