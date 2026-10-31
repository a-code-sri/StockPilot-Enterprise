"""
Small, dependency-free statistics helpers shared by analytics and anomaly detection.
"""

from __future__ import annotations

from statistics import median
from typing import Sequence

# Iglewicz & Hoaglin: |modified z| > 3.5 is a common outlier threshold.
DEFAULT_Z_THRESHOLD = 3.5
MIN_SAMPLES = 5


def mad(values: Sequence[float]) -> float:
    """Median absolute deviation."""
    if not values:
        return 0.0
    m = median(values)
    return median([abs(v - m) for v in values])


def modified_z_scores(values: Sequence[float]) -> list[float]:
    """
    Robust z-scores based on median/MAD (insensitive to the outliers we look for).
    Falls back to mean absolute deviation when MAD is 0 (e.g. many identical values).
    """
    if not values:
        return []
    m = median(values)
    spread = mad(values)
    if spread == 0:
        mean_abs = sum(abs(v - m) for v in values) / len(values)
        if mean_abs == 0:
            return [0.0 for _ in values]
        return [(v - m) / (1.253314 * mean_abs) for v in values]
    return [0.6745 * (v - m) / spread for v in values]


def find_outliers(
    values: Sequence[float],
    *,
    threshold: float = DEFAULT_Z_THRESHOLD,
    min_samples: int = MIN_SAMPLES,
    high_only: bool = True,
) -> list[tuple[int, float]]:
    """Returns (index, score) for each outlier. Needs at least `min_samples` values."""
    if len(values) < min_samples:
        return []
    out = []
    for i, z in enumerate(modified_z_scores(values)):
        if (z >= threshold) if high_only else (abs(z) >= threshold):
            out.append((i, z))
    return out


def histogram(values: Sequence[float], bins: int) -> list[dict[str, float]]:
    """Equal-width histogram as [{bin_start, bin_end, count}]; max value lands in the last bin."""
    bins = max(1, int(bins))
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [{"bin_start": lo, "bin_end": hi, "count": float(len(values))}]
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        counts[min(bins - 1, max(0, int((v - lo) / width)))] += 1
    return [
        {"bin_start": lo + i * width, "bin_end": lo + (i + 1) * width, "count": float(c)}
        for i, c in enumerate(counts)
    ]
