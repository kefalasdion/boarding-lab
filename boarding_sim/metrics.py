"""Stable metric definitions and passenger-level distribution summaries."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from .models import (
    AccessResult,
    AircraftResult,
    DistributionSummary,
    Passenger,
    PreparationResult,
)
from .stats import mean, quantile


def summarize_distribution(values: Iterable[float]) -> DistributionSummary | None:
    data = list(values)
    if not data:
        return None
    average = mean(data)
    if len(data) > 1:
        variance = sum((value - average) ** 2 for value in data) / (len(data) - 1)
        margin = 1.96 * math.sqrt(variance) / math.sqrt(len(data))
    else:
        margin = 0.0
    return DistributionSummary(
        count=len(data),
        minimum=min(data),
        p10=quantile(data, 0.10),
        p50=quantile(data, 0.50),
        mean=average,
        p90=quantile(data, 0.90),
        p95=quantile(data, 0.95),
        maximum=max(data),
        mean_ci95_low=average - margin,
        mean_ci95_high=average + margin,
    )


def build_metrics(
    passengers: list[Passenger],
    scenario: dict[str, Any],
    preparation: PreparationResult,
    access: AccessResult,
    aircraft: AircraftResult,
) -> dict[str, Any]:
    threshold = scenario["metrics"]["frustrationThreshold"]
    total_seconds = aircraft.last_seat_time
    embarkation_seconds = (
        None
        if total_seconds is None
        else total_seconds - preparation.time_seconds
    )
    total_burden = summarize_distribution(
        passenger.frustration_burden for passenger in passengers
    )
    return {
        "timings_seconds": {
            "preparation": preparation.time_seconds,
            "access_until_last_door_arrival": access.transfer_end_seconds
            - preparation.time_seconds,
            "embarkation": embarkation_seconds,
            "cabin_boarding": aircraft.cabin_boarding_seconds,
            "total_t0_to_last_seat": total_seconds,
        },
        "passenger_experience": {
            "initial_frustration": summarize_distribution(
                passenger.initial_frustration for passenger in passengers
            ),
            "preparation_frustration_burden_f_minutes": summarize_distribution(
                passenger.preparation_frustration_burden
                for passenger in passengers
            ),
            "embarkation_frustration_burden_f_minutes": summarize_distribution(
                passenger.embarkation_frustration_burden
                for passenger in passengers
            ),
            "total_frustration_burden_f_minutes": total_burden,
            "frustration_burden_f_minutes": total_burden,
            "peak_frustration": summarize_distribution(
                passenger.peak_frustration for passenger in passengers
            ),
            "time_above_threshold_minutes": summarize_distribution(
                passenger.time_above_threshold_seconds / 60.0
                for passenger in passengers
            ),
            "threshold": threshold,
            "share_peak_above_threshold": sum(
                passenger.peak_frustration > threshold for passenger in passengers
            )
            / len(passengers),
        },
        "correction_events": preparation.corrections,
        "companion_overrides": sum(
            passenger.companion_override for passenger in passengers
        ),
        "seated_count": aircraft.seated_count,
        "passenger_count": len(passengers),
        "preparation_timed_out": preparation.timed_out,
        "aircraft_timed_out": aircraft.timed_out,
    }


def build_preparation_timeout_metrics(
    passengers: list[Passenger],
    scenario: dict[str, Any],
    preparation: PreparationResult,
) -> dict[str, Any]:
    """Describe an incomplete preparation without inventing boarding outcomes."""
    threshold = scenario["metrics"]["frustrationThreshold"]
    preparation_burden = summarize_distribution(
        passenger.preparation_frustration_burden for passenger in passengers
    )
    zero_embarkation = summarize_distribution(0.0 for _passenger in passengers)
    return {
        "timings_seconds": {
            "preparation": preparation.time_seconds,
            "access_until_last_door_arrival": None,
            "embarkation": None,
            "cabin_boarding": None,
            "total_t0_to_last_seat": None,
        },
        "passenger_experience": {
            "initial_frustration": summarize_distribution(
                passenger.initial_frustration for passenger in passengers
            ),
            "preparation_frustration_burden_f_minutes": preparation_burden,
            "embarkation_frustration_burden_f_minutes": zero_embarkation,
            "total_frustration_burden_f_minutes": preparation_burden,
            "frustration_burden_f_minutes": preparation_burden,
            "peak_frustration": summarize_distribution(
                passenger.peak_frustration for passenger in passengers
            ),
            "time_above_threshold_minutes": summarize_distribution(
                passenger.time_above_threshold_seconds / 60.0
                for passenger in passengers
            ),
            "threshold": threshold,
            "share_peak_above_threshold": sum(
                passenger.peak_frustration > threshold for passenger in passengers
            )
            / len(passengers),
        },
        "correction_events": preparation.corrections,
        "companion_overrides": sum(
            passenger.companion_override for passenger in passengers
        ),
        "seated_count": 0,
        "passenger_count": len(passengers),
        "preparation_timed_out": True,
        "aircraft_timed_out": False,
    }
