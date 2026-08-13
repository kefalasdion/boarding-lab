"""Latent passenger stress and provisional frustration mapping."""

from __future__ import annotations

import math
from typing import Any

from .models import Passenger


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def logistic(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def frustration_from_load(passenger: Passenger, calibration: dict[str, Any]) -> float:
    return logistic(
        (passenger.stress_load - passenger.tolerance_threshold)
        / calibration["frustrationSlope"]
    )


def evolve_passenger(
    passenger: Passenger,
    dt_seconds: float,
    load_rate_per_minute: float,
    recovery_rate_per_minute: float,
    calibration: dict[str, Any],
    frustration_threshold: float,
) -> None:
    if dt_seconds <= 0:
        return
    dt_minutes = dt_seconds / 60.0
    passenger.stress_load = clamp(
        passenger.stress_load
        + dt_minutes * (load_rate_per_minute - recovery_rate_per_minute),
        0.0,
        2.0,
    )
    passenger.frustration = frustration_from_load(passenger, calibration)
    passenger.frustration_burden += passenger.frustration * dt_minutes
    passenger.peak_frustration = max(passenger.peak_frustration, passenger.frustration)
    if passenger.frustration > frustration_threshold:
        passenger.time_above_threshold_seconds += dt_seconds


def initial_stress_load(
    passenger: Passenger,
    scenario: dict[str, Any],
    calibration: dict[str, Any],
) -> float:
    context = scenario["flightContext"]
    coeff = calibration["initial"]
    delay_term = (
        coeff["delay"]
        * passenger.delay_sensitivity
        * math.log1p(context["delayMinutes"] / 15.0)
    )
    gate_wait_term = (
        coeff["priorGateWait"]
        * passenger.wait_sensitivity
        * math.log1p(context["priorGateWaitMinutes"] / 30.0)
    )
    dwell_term = (
        coeff["airportDwell"]
        * passenger.fatigue
        * math.log1p(context["priorAirportDwellMinutes"] / 60.0)
    )
    uncertainty_term = (
        coeff["uncertainty"]
        * passenger.uncertainty_sensitivity
        * (1.0 - passenger.information_trust)
    )
    fatigue_term = coeff["fatigue"] * passenger.fatigue
    connection_term = coeff["connection"] * passenger.connection_pressure
    information_term = (
        coeff["unreliableInformation"]
        * (1.0 - passenger.information_trust)
        * min(1.0, context["priorDelayUpdates"] / 3.0)
    )
    return clamp(
        delay_term
        + gate_wait_term
        + dwell_term
        + uncertainty_term
        + fatigue_term
        + connection_term
        + information_term,
        0.0,
        1.5,
    )
