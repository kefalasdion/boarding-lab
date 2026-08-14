"""Correlated passenger population and T=0 state generation."""

from __future__ import annotations

from typing import Any

from .frustration import clamp, frustration_from_load, initial_stress_load
from .models import Passenger
from .prng import RNG
from .strategies import Strategy, apply_companion_policy

SEATS = ("A", "B", "C", "D", "E", "F")


def _family_assignments(count: int, target_share: float, rng: RNG) -> list[int]:
    assignments = [0] * count
    target = min(count, max(0, round(count * target_share)))
    if target == 1:
        target = 2 if count >= 2 else 0
    indices = list(rng.shuffle(list(range(count))))
    cursor = 0
    family_id = 1
    assigned = 0
    while target - assigned >= 2 and cursor < count:
        remaining = target - assigned
        draw = rng.next()
        size = 4 if draw < 0.22 else 3 if rng.next() < 0.55 else 2
        size = min(size, remaining, count - cursor)
        if remaining - size == 1 and size > 2:
            size -= 1
        if size < 2:
            break
        for _ in range(size):
            assignments[indices[cursor]] = family_id
            cursor += 1
        assigned += size
        family_id += 1
    if target - assigned == 1 and family_id > 1 and cursor < count:
        assignments[indices[cursor]] = family_id - 1
    return assignments


def _selected_seats(scenario: dict[str, Any], rng: RNG) -> list[tuple[int, str]]:
    seats = [
        (row, seat)
        for row in range(1, scenario["aircraft"]["rows"] + 1)
        for seat in SEATS[: scenario["aircraft"]["seatsPerRow"]]
    ]
    target = round(len(seats) * scenario["aircraft"]["loadFactor"])
    if target < len(seats):
        shuffled = list(rng.shuffle(seats.copy()))
        seats = sorted(shuffled[:target], key=lambda item: (item[0], SEATS.index(item[1])))
    return seats


def generate_manifest(
    scenario: dict[str, Any],
    rng: RNG,
    calibration: dict[str, Any],
) -> list[Passenger]:
    seats = _selected_seats(scenario, rng.fork(17))
    family_ids = _family_assignments(
        len(seats), scenario["population"]["familyPassengerShare"], rng.fork(31)
    )
    context = scenario["flightContext"]
    population_config = scenario["population"]
    passengers: list[Passenger] = []
    for passenger_id, ((row, seat), family_id) in enumerate(zip(seats, family_ids)):
        self_regulation = rng.normal()
        stress_reactivity = rng.normal()
        social_factor = rng.normal()
        mobility = rng.normal()
        tolerance = clamp(0.55 + 0.13 * self_regulation - 0.07 * stress_reactivity + rng.normal(0, 0.05), 0.16, 0.92)
        delay = clamp(0.50 - 0.12 * self_regulation + 0.16 * stress_reactivity + rng.normal(0, 0.06), 0.05, 0.98)
        uncertainty = clamp(0.48 - 0.10 * self_regulation + 0.15 * stress_reactivity + rng.normal(0, 0.07), 0.05, 0.98)
        waiting = clamp(0.48 - 0.10 * self_regulation + 0.12 * stress_reactivity + rng.normal(0, 0.07), 0.05, 0.98)
        crowd = clamp(0.44 + 0.16 * stress_reactivity + rng.normal(0, 0.07), 0.05, 0.98)
        social = clamp(0.46 + 0.18 * social_factor + rng.normal(0, 0.07), 0.03, 0.98)
        compliance = clamp(0.83 + 0.09 * self_regulation - 0.08 * stress_reactivity + rng.normal(0, 0.06), 0.25, 0.99)
        trust = clamp(0.88 - 0.055 * context["priorDelayUpdates"] - 0.0015 * context["delayMinutes"] + rng.normal(0, 0.06), 0.12, 0.98)
        fatigue = clamp(0.19 + 0.07 * stress_reactivity + 0.0015 * context["priorAirportDwellMinutes"] + (0.04 if family_id else 0.0) + rng.normal(0, 0.05), 0.02, 0.95)
        connection = clamp(0.55 + rng.normal(0, 0.16), 0.15, 1.0) if rng.boolean(context["connectionPressureShare"]) else clamp(0.08 + rng.normal(0, 0.05), 0.0, 0.25)
        urgency = clamp(0.20 + 0.45 * connection + 0.15 * delay + rng.normal(0, 0.07), 0.02, 0.98)
        walking_speed = clamp(0.80 + 0.10 * mobility - 0.08 * fatigue + rng.normal(0, 0.06), 0.45, 1.15)
        has_bag = rng.boolean(population_config["handLuggageShare"])
        bag_count = 0 if not has_bag else 2 if rng.boolean(population_config["twoBagShareAmongBagPassengers"]) else 1
        passenger = Passenger(
            id=passenger_id,
            row=row,
            seat=seat,
            family_id=family_id,
            tolerance_threshold=tolerance,
            delay_sensitivity=delay,
            uncertainty_sensitivity=uncertainty,
            wait_sensitivity=waiting,
            crowd_sensitivity=crowd,
            social_susceptibility=social,
            compliance=compliance,
            information_trust=trust,
            fatigue=fatigue,
            connection_pressure=connection,
            urgency=urgency,
            walking_speed_mps=walking_speed,
            bag_count=bag_count,
        )
        passenger.stress_load = initial_stress_load(passenger, scenario, calibration)
        passenger.initial_stress_load = passenger.stress_load
        passenger.frustration = frustration_from_load(passenger, calibration)
        passenger.initial_frustration = passenger.frustration
        passenger.peak_frustration = passenger.frustration
        passengers.append(passenger)
    return passengers


def assign_strategy(
    passengers: list[Passenger], strategy: Strategy, rng: RNG
) -> list[Passenger]:
    return apply_companion_policy(passengers, strategy, rng.fork(71))


def generate_population(
    scenario: dict[str, Any],
    strategy: Strategy,
    rng: RNG,
    calibration: dict[str, Any],
) -> list[Passenger]:
    return assign_strategy(generate_manifest(scenario, rng, calibration), strategy, rng)
