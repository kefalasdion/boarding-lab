"""Small deterministic statistical helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable


def mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0.0


def quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
