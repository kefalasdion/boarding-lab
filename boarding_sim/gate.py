"""Deterministic gate geometry and strategy-specific queue plans."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .models import GateLayout, GatePlan, GatePoint, Passenger, QueueSlot
from .prng import RNG
from .strategies import Strategy


def _point(x_m: float, y_m: float) -> GatePoint:
    return GatePoint(round(x_m, 3), round(y_m, 3))


def _axis_values(limit: float, spacing: float) -> list[float]:
    margin = spacing / 2.0
    values: list[float] = []
    value = margin
    while value <= limit - margin + 1e-9:
        values.append(round(value, 3))
        value += spacing
    return values


def _start_candidates(layout: GateLayout, spacing: float) -> list[GatePoint]:
    return [
        _point(x_m, y_m)
        for y_m in _axis_values(layout.height_m, spacing)
        for x_m in _axis_values(layout.width_m, spacing)
    ]


def _cohort_points(
    count: int,
    cohort: int,
    cohort_count: int,
    layout: GateLayout,
    spacing: float,
) -> list[GatePoint]:
    x_values = list(reversed(_axis_values(layout.width_m - spacing, spacing)))
    if not x_values:
        raise ValueError("Gate width cannot hold a queue lane.")
    band_height = layout.height_m / max(1, cohort_count)
    band_low = cohort * band_height
    band_high = min(layout.height_m, band_low + band_height)
    row_count = max(1, math.ceil(count / len(x_values)))
    if row_count == 1:
        y_values = [(band_low + band_high) / 2.0]
    else:
        inset = min(spacing / 2.0, band_height / (row_count + 1))
        usable = max(0.0, band_height - 2.0 * inset)
        y_values = [
            band_low + inset + usable * index / max(1, row_count - 1)
            for index in range(row_count)
        ]
    points: list[GatePoint] = []
    for row_index, y_m in enumerate(y_values):
        row = x_values if row_index % 2 == 0 else list(reversed(x_values))
        for x_m in row:
            points.append(_point(x_m, y_m))
            if len(points) == count:
                return points
    if len(points) < count:
        raise ValueError("Gate geometry cannot hold every queue slot.")
    return points


def build_gate_plan(
    passengers: list[Passenger],
    scenario: dict[str, Any],
    strategy: Strategy,
    rng: RNG,
) -> GatePlan:
    config = scenario["preparation"]
    area = float(config["gateUsableAreaM2"])
    aspect_ratio = float(config["gateAspectRatio"])
    spacing = float(config["queueLaneSpacingM"])
    width_m = math.sqrt(area * aspect_ratio)
    height_m = area / width_m
    layout = GateLayout(
        width_m=round(width_m, 3),
        height_m=round(height_m, 3),
        boarding_control=_point(width_m, height_m / 2.0),
    )

    candidates = _start_candidates(layout, spacing)
    if len(candidates) < len(passengers):
        raise ValueError("Gate geometry cannot hold every passenger start position.")
    rng.shuffle(candidates)
    start_positions = {
        passenger.id: candidates[index]
        for index, passenger in enumerate(sorted(passengers, key=lambda item: item.id))
    }

    ordered = sorted(
        passengers,
        key=lambda passenger: (passenger.boarding_rank, passenger.id),
    )
    by_cohort: dict[int, list[Passenger]] = defaultdict(list)
    for passenger in ordered:
        by_cohort[passenger.prep_cohort].append(passenger)
    cohorts = sorted(by_cohort)
    cohort_index = {cohort: index for index, cohort in enumerate(cohorts)}
    points_by_cohort = {
        cohort: _cohort_points(
            len(by_cohort[cohort]),
            cohort_index[cohort],
            len(cohorts),
            layout,
            spacing,
        )
        for cohort in cohorts
    }
    next_point = {cohort: 0 for cohort in cohorts}
    slots: list[QueueSlot] = []
    for slot_index, passenger in enumerate(ordered):
        cohort = passenger.prep_cohort
        point = points_by_cohort[cohort][next_point[cohort]]
        next_point[cohort] += 1
        slots.append(QueueSlot(passenger.id, slot_index, cohort, point))
    queue_slots = {slot.passenger_id: slot.point for slot in slots}
    if len(set(queue_slots.values())) != len(queue_slots):
        raise ValueError("Queue-slot geometry produced overlapping passengers.")
    return GatePlan(layout, start_positions, slots, queue_slots)
