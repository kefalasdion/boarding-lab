"""Gate-agent call schedule that makes passengers eligible to form the line.

Preparation has two distinct actions: a passenger becomes eligible after the
appropriate call, and only then does the behaviour model govern response,
walking, crowding, mistakes, correction and staging. This module owns the
first action. It is deterministic and consumes no random numbers.
"""

from __future__ import annotations

from typing import Any

from .models import Passenger, SimulationEvent
from .strategies import Strategy, strategy_release_mode


def _cohort_order(passengers: list[Passenger]) -> dict[int, int]:
    cohorts = sorted({passenger.prep_cohort for passenger in passengers})
    return {cohort: index for index, cohort in enumerate(cohorts)}


def release_schedule(
    passengers: list[Passenger],
    strategy: Strategy,
    release: dict[str, Any],
) -> dict[int, float]:
    """Return the time at which each passenger becomes eligible to move.

    `release` is the scenario's `preparation.release` block. The call rate is a
    property of the gate operation being modelled, not of passenger psychology,
    which is why it is a scenario input rather than a behaviour coefficient.
    """
    mode = strategy_release_mode(strategy)
    if mode == "general":
        return {passenger.id: 0.0 for passenger in passengers}

    intervals = release
    if mode == "individual":
        interval = float(intervals["passengerIntervalSeconds"])
        return {
            passenger.id: round(passenger.boarding_rank * interval, 6)
            for passenger in passengers
        }

    interval = float(intervals["zoneIntervalSeconds"])
    order = _cohort_order(passengers)
    return {
        passenger.id: round(order[passenger.prep_cohort] * interval, 6)
        for passenger in passengers
    }


def release_events(
    passengers: list[Passenger],
    strategy: Strategy,
    schedule: dict[int, float],
) -> list[SimulationEvent]:
    """Return the gate-agent call events for this strategy at their modeled times."""
    mode = strategy_release_mode(strategy)
    if mode == "general":
        return [
            SimulationEvent(
                "preparation_general_call",
                0.0,
                None,
                {"passenger_count": len(passengers)},
            )
        ]

    if mode == "individual":
        ordered = sorted(passengers, key=lambda item: (schedule[item.id], item.id))
        return [
            SimulationEvent(
                "preparation_passenger_called", schedule[passenger.id], passenger.id
            )
            for passenger in ordered
        ]

    cohorts: dict[int, list[Passenger]] = {}
    for passenger in passengers:
        cohorts.setdefault(passenger.prep_cohort, []).append(passenger)
    return [
        SimulationEvent(
            "preparation_zone_called",
            schedule[members[0].id],
            None,
            {"cohort": cohort, "passenger_count": len(members)},
        )
        for cohort, members in sorted(cohorts.items())
    ]
