from datetime import date

import pytest

from backend.core.analytics.stats import find_outliers, histogram, modified_z_scores
from backend.modules.accounts.application.analytics_service import liquidity_score
from backend.modules.accounts.application.anomalies import detect_transaction_anomalies
from backend.modules.delivery.analytics_router import moving_average_series, shift_hours
from backend.modules.inventory.application.analytics_service import days_to_stockout, reorder_quantity


def test_robust_z_flags_spike_only():
    values = [10, 11, 9, 10, 12, 10, 100]
    assert [i for i, _ in find_outliers(values)] == [6]
    assert find_outliers([1, 2, 3]) == []  # too few samples


def test_z_scores_when_mad_is_zero():
    zs = modified_z_scores([5, 5, 5, 5, 50])
    assert zs[-1] > 3.5 and zs[0] == 0


def test_histogram_bins_and_max_in_last_bin():
    h = histogram([0, 5, 10], 2)
    assert [b["count"] for b in h] == [1.0, 2.0]
    assert histogram([7, 7], 5) == [{"bin_start": 7, "bin_end": 7, "count": 2.0}]
    assert histogram([], 3) == []


def _tx(i, amount, cat="Rent", t="debit"):
    return {"id": i, "amount": amount, "transaction_type": t, "category": cat, "source_target": "x",
            "date": "2026-01-01"}


def test_transaction_anomaly_within_category():
    txs = [_tx(i, 1000 + i) for i in range(8)] + [_tx(99, 25000)]
    found = detect_transaction_anomalies(txs)
    assert [a["transaction_id"] for a in found] == [99]
    assert "x the typical" in found[0]["reason"]


def test_small_category_falls_back_to_type():
    txs = [_tx(i, 100 + i, cat="Supplies") for i in range(6)] + [_tx(50, 9000, cat="Travel")]
    assert [a["transaction_id"] for a in detect_transaction_anomalies(txs)] == [50]


def test_liquidity_score_bounds():
    healthy = liquidity_score(current_balance=100000, total_credit=50000, total_debit=10000, days=30)
    broke = liquidity_score(current_balance=-500, total_credit=0, total_debit=10000, days=30)
    assert 90 <= healthy["score"] <= 100
    assert broke["score"] < 10
    assert liquidity_score(current_balance=0, total_credit=0, total_debit=0, days=30)["buffer_days"] is None


def test_inventory_formulas():
    assert reorder_quantity(rate=2, coverage_days=14, quantity=10, on_order=5) == 13
    assert reorder_quantity(rate=0, coverage_days=14, quantity=0, on_order=0) == 0
    assert days_to_stockout(rate=2, quantity=10) == 5
    assert days_to_stockout(rate=0, quantity=10) is None


def test_moving_average_fills_missing_days():
    s = moving_average_series({date(2026, 1, 1): 4, date(2026, 1, 3): 2}, date(2026, 1, 1), date(2026, 1, 3), 2)
    assert [x["count"] for x in s] == [4, 0, 2]
    assert [x["moving_avg"] for x in s] == [4, 2, 1]


def test_hour_shift_for_ist():
    shifted = shift_hours({23: 3, 4: 1}, 330)  # +5:30 rounds to +6h
    assert shifted[5]["value"] == 3 and shifted[10]["value"] == 1
    assert sum(h["value"] for h in shifted) == 4


@pytest.mark.parametrize("bins", [1, 3, 10])
def test_histogram_counts_everything(bins):
    data = [1, 2, 2, 3, 8, 9, 15]
    assert sum(b["count"] for b in histogram(data, bins)) == len(data)
