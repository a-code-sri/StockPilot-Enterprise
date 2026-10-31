"""
Statistical anomaly detection for transactions (no AI involved).

A transaction is flagged when its amount is an outlier compared with other
transactions of the same type and category (robust median/MAD z-score). Small
categories fall back to comparing against all transactions of the same type.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any, Iterable

from backend.core.analytics.stats import DEFAULT_Z_THRESHOLD, MIN_SAMPLES, modified_z_scores


def _anomaly(t: dict, typical: float, z: float, scope: str) -> dict[str, Any]:
    if typical:
        reason = f"{t['amount']:,.2f} is {t['amount'] / typical:.1f}x the typical {scope} amount of {typical:,.2f}"
    else:
        reason = f"Unusually large compared with other {scope} transactions"
    return {
        "transaction_id": t["id"],
        "date": t["date"],
        "transaction_type": t["transaction_type"],
        "category": t["category"],
        "source_target": t["source_target"],
        "amount": round(t["amount"], 2),
        "typical_amount": round(typical, 2),
        "score": round(z, 2),
        "reason": reason,
    }


def detect_transaction_anomalies(
    transactions: Iterable[dict[str, Any]],
    *,
    threshold: float = DEFAULT_Z_THRESHOLD,
    min_samples: int = MIN_SAMPLES,
) -> list[dict[str, Any]]:
    """
    `transactions`: dicts with id, amount, transaction_type, category, source_target, date.
    Returns flagged transactions, most anomalous first.
    """
    txs = [dict(t, amount=float(t["amount"])) for t in transactions]

    by_category: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_type: dict[str, list[dict]] = defaultdict(list)
    for t in txs:
        by_category[(t["transaction_type"], t["category"])].append(t)
        by_type[t["transaction_type"]].append(t)

    type_scores: dict[str, tuple[float, dict[Any, float]]] = {}
    for ttype, group in by_type.items():
        amounts = [t["amount"] for t in group]
        type_scores[ttype] = (median(amounts), dict(zip((t["id"] for t in group), modified_z_scores(amounts))))

    flagged: list[dict[str, Any]] = []
    for (ttype, category), group in by_category.items():
        if len(group) >= min_samples:
            amounts = [t["amount"] for t in group]
            typical = median(amounts)
            scored = zip(group, modified_z_scores(amounts))
            scope = f"'{category}' {ttype}"
        elif len(by_type[ttype]) >= min_samples:
            # Too few samples in this category; compare against the whole type.
            typical, scores = type_scores[ttype]
            scored = ((t, scores[t["id"]]) for t in group)
            scope = ttype
        else:
            continue

        flagged.extend(_anomaly(t, typical, z, scope) for t, z in scored if z >= threshold)

    return sorted(flagged, key=lambda a: a["score"], reverse=True)
