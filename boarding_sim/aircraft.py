"""Synchronous 0.4 m-cell aircraft boarding cellular automaton."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, TypeVar

from .access import access_rates, access_state_at
from .frustration import evolve_passenger
from .models import (
    AccessResult,
    AircraftResult,
    MovementEvent,
    Passenger,
    ProgressSample,
    SimulationEvent,
)
from .prng import RNG
from .stats import mean, quantile

T = TypeVar("T")


@dataclass
class _AisleRecord:
    passenger: Passenger
    cell: int
    door: str
    state: str = "walking"
    move_credit: float = 0.0
    service_end_time: float | None = None


def _target_cell(passenger: Passenger, config: dict[str, Any]) -> int:
    return (passenger.row - 1) * config["aisleCellsPerRow"] + (
        config["aisleCellsPerRow"] - 1
    )


def _seat_movement_count(passenger: Passenger, occupied_seats: set[tuple[int, str]]) -> int:
    def occupied(seat: str) -> bool:
        return (passenger.row, seat) in occupied_seats

    if passenger.seat in {"C", "D"}:
        return 1
    if passenger.seat == "B":
        return 4 if occupied("C") else 1
    if passenger.seat == "E":
        return 4 if occupied("D") else 1
    if passenger.seat == "A":
        middle, aisle = occupied("B"), occupied("C")
    else:
        middle, aisle = occupied("E"), occupied("D")
    if middle and aisle:
        return 9
    if middle:
        return 5
    if aisle:
        return 4
    return 1


def custom_service_seconds(seated_fraction: float, config: dict[str, Any]) -> float:
    if seated_fraction < config["customLoadThreshold"]:
        return config["customSeatBaseSeconds"]
    steps = (
        math.floor(
            (seated_fraction - config["customLoadThreshold"])
            / config["customIncrementLoadStep"]
            + 1e-9
        )
        + 1
    )
    return config["customSeatBaseSeconds"] + steps * config["customIncrementSeconds"]


def _row_service(
    passenger: Passenger,
    occupied_seats: set[tuple[int, str]],
    seated_count: int,
    total: int,
    config: dict[str, Any],
    rng: RNG,
) -> dict[str, float | str | int]:
    if config["serviceModel"] == "user_occupancy_rule":
        duration = custom_service_seconds(seated_count / total, config)
        return {
            "model": "user_occupancy_rule",
            "durationSeconds": duration,
            "baggageSeconds": 0.0,
            "seatShuffleSeconds": 0.0,
            "seatMovements": 0,
        }
    baggage = sum(
        rng.weibull(
            config["baggageWeibullShape"],
            config["baggageWeibullScaleSeconds"],
        )
        for _ in range(passenger.bag_count)
    )
    movements = _seat_movement_count(passenger, occupied_seats)
    minimum, mode, maximum = config["seatMovementTriangularSeconds"]
    seat_shuffle = sum(
        rng.triangular(minimum, mode, maximum) for _ in range(movements)
    )
    return {
        "model": "field_calibrated",
        "durationSeconds": baggage + seat_shuffle,
        "baggageSeconds": baggage,
        "seatShuffleSeconds": seat_shuffle,
        "seatMovements": movements,
    }


def resolve_conflict(contenders: list[T], rng: RNG) -> T:
    if not contenders:
        raise ValueError("At least one contender is required.")
    if len(contenders) == 1:
        return contenders[0]
    return contenders[int(rng.next() * len(contenders))]


def _snapshot(
    passengers: list[Passenger],
    access: AccessResult,
    time_seconds: float,
    entered_count: int,
    seated_count: int,
) -> ProgressSample:
    active = [passenger for passenger in passengers if not passenger.seated]
    frustrations = [passenger.frustration for passenger in (active or passengers)]
    return ProgressSample(
        time_seconds=time_seconds,
        phase="embarkation",
        mean_frustration=mean(frustrations),
        p90_frustration=quantile(frustrations, 0.9),
        prepared_count=sum(passenger.prep_correct for passenger in passengers),
        access_arrived_count=sum(
            arrival.ready_time <= time_seconds for arrival in access.arrivals
        ),
        entered_count=entered_count,
        seated_count=seated_count,
    )


def simulate_aircraft(
    passengers: list[Passenger],
    access: AccessResult,
    scenario: dict[str, Any],
    rng: RNG,
    calibration: dict[str, Any],
    phase_start_seconds: float,
) -> AircraftResult:
    config = scenario["boarding"]
    cabin_coefficients = calibration["cabinPerMinute"]
    threshold = scenario["metrics"]["frustrationThreshold"]
    sample_seconds = scenario["metrics"]["historySampleSeconds"]
    total = len(passengers)
    aisle_cell_count = scenario["aircraft"]["rows"] * config["aisleCellsPerRow"]
    dt = config["dtSeconds"]
    first_ready = min(arrival.ready_time for arrival in access.arrivals)
    arrivals_by_id = {arrival.passenger_id: arrival for arrival in access.arrivals}
    passengers_by_id = {passenger.id: passenger for passenger in passengers}
    queues = {
        door: sorted(
            [arrival for arrival in access.arrivals if arrival.door == door],
            key=lambda arrival: (
                arrival.ready_time,
                passengers_by_id[arrival.passenger_id].boarding_rank,
                arrival.passenger_id,
            ),
        )
        for door in ("front", "rear")
    }
    entered: set[int] = set()
    occupied_seats: set[tuple[int, str]] = set()
    in_aisle: dict[int, _AisleRecord] = {}
    events: list[SimulationEvent] = []
    movement_audit: list[MovementEvent] = []
    history = [_snapshot(passengers, access, phase_start_seconds, 0, 0)]
    next_sample_time = phase_start_seconds + sample_seconds
    time_seconds = phase_start_seconds
    first_entry_time: float | None = None
    last_seat_time: float | None = None
    seated_count = 0
    conflict_count = 0
    max_aisle_occupancy = 0
    occupancy_violations = 0
    simultaneous_aisle_seat_violations = 0
    duplicate_seat_count = 0
    minimum_service_remaining: float | None = None

    for passenger in passengers:
        passenger.seated = False
        passenger.aircraft_state = "not_arrived"

    while seated_count < total and time_seconds - first_ready < config["maxBoardingSeconds"]:
        for passenger_id, record in list(in_aisle.items()):
            if record.state != "service" or record.service_end_time is None:
                continue
            remaining = max(0.0, record.service_end_time - time_seconds)
            minimum_service_remaining = remaining if minimum_service_remaining is None else min(minimum_service_remaining, remaining)
            if remaining <= 1e-9:
                passenger = record.passenger
                seat_key = (passenger.row, passenger.seat)
                if seat_key in occupied_seats:
                    duplicate_seat_count += 1
                occupied_seats.add(seat_key)
                passenger.seated = True
                passenger.aircraft_state = "seated"
                seated_count += 1
                del in_aisle[passenger_id]
                last_seat_time = time_seconds
                events.append(
                    SimulationEvent(
                        "seated",
                        time_seconds,
                        passenger.id,
                        {"row": passenger.row, "seat": passenger.seat},
                    )
                )

        for record in list(in_aisle.values()):
            if record.state == "walking" and record.cell == _target_cell(record.passenger, config):
                service = _row_service(
                    record.passenger,
                    occupied_seats,
                    seated_count,
                    total,
                    config,
                    rng,
                )
                record.state = "service"
                record.service_end_time = time_seconds + float(service["durationSeconds"])
                record.passenger.aircraft_state = "row_service"
                events.append(
                    SimulationEvent(
                        "row_service_started",
                        time_seconds,
                        record.passenger.id,
                        {
                            **service,
                            "targetCell": record.cell,
                        },
                    )
                )

        occupancy = {record.cell: record for record in in_aisle.values()}
        if len(occupancy) != len(in_aisle):
            occupancy_violations += 1
        max_aisle_occupancy = max(max_aisle_occupancy, len(occupancy))
        proposals: dict[int, list[_AisleRecord]] = {}
        for record in list(in_aisle.values()):
            passenger = record.passenger
            if record.state == "service":
                evolve_passenger(
                    passenger,
                    dt,
                    cabin_coefficients["rowServiceEffort"],
                    0.0,
                    calibration,
                    threshold,
                )
                continue
            target = _target_cell(passenger, config)
            if record.cell == target:
                continue
            record.move_credit += (
                min(passenger.walking_speed_mps, config["walkingSpeedMps"])
                * dt
                / config["cellSizeM"]
            )
            if record.move_credit < 1.0:
                evolve_passenger(
                    passenger,
                    dt,
                    cabin_coefficients["aisleBlocked"] * 0.25,
                    0.0,
                    calibration,
                    threshold,
                )
                continue
            direction = 1 if target > record.cell else -1
            next_cell = record.cell + direction
            if (
                next_cell < 0
                or next_cell >= aisle_cell_count
                or next_cell in occupancy
            ):
                evolve_passenger(
                    passenger,
                    dt,
                    cabin_coefficients["aisleBlocked"] * passenger.wait_sensitivity,
                    0.0,
                    calibration,
                    threshold,
                )
                continue
            proposals.setdefault(next_cell, []).append(record)

        for target_cell, contenders in sorted(proposals.items()):
            winner = resolve_conflict(contenders, rng)
            if len(contenders) > 1:
                conflict_count += len(contenders) - 1
            old_cell = winner.cell
            winner.cell = target_cell
            winner.move_credit -= 1.0
            winner.passenger.aircraft_state = "aisle_moving"
            movement_audit.append(
                MovementEvent(
                    time_seconds,
                    winner.passenger.id,
                    winner.door,
                    old_cell,
                    target_cell,
                    _target_cell(winner.passenger, config),
                )
            )
            evolve_passenger(
                winner.passenger,
                dt,
                0.0,
                cabin_coefficients["aisleMovingRecovery"],
                calibration,
                threshold,
            )
            for loser in contenders:
                if loser is winner:
                    continue
                evolve_passenger(
                    loser.passenger,
                    dt,
                    cabin_coefficients["aisleBlocked"]
                    * loser.passenger.wait_sensitivity,
                    0.0,
                    calibration,
                    threshold,
                )

        for passenger in passengers:
            if passenger.id in entered or passenger.seated:
                continue
            arrival = arrivals_by_id[passenger.id]
            midpoint = time_seconds + dt / 2.0
            if midpoint < arrival.ready_time:
                state = access_state_at(access, passenger.id, midpoint)
                passenger.access_state = state or "approaching_door"
                load_rate, recovery_rate = access_rates(passenger, state or "", calibration)
                evolve_passenger(
                    passenger,
                    dt,
                    load_rate,
                    recovery_rate,
                    calibration,
                    threshold,
                )
            elif passenger.id not in in_aisle:
                passenger.aircraft_state = "door_queue"
                evolve_passenger(
                    passenger,
                    dt,
                    cabin_coefficients["doorQueue"] * passenger.wait_sensitivity,
                    0.0,
                    calibration,
                    threshold,
                )

        current_occupancy = {record.cell: record for record in in_aisle.values()}
        for door in ("front", "rear"):
            next_arrival = next(
                (
                    arrival
                    for arrival in queues[door]
                    if arrival.passenger_id not in entered
                    and arrival.ready_time <= time_seconds
                ),
                None,
            )
            if next_arrival is None:
                continue
            entry_cell = 0 if door == "front" else aisle_cell_count - 1
            if entry_cell in current_occupancy:
                continue
            passenger = passengers_by_id[next_arrival.passenger_id]
            entered.add(passenger.id)
            passenger.aircraft_state = "aisle_moving"
            record = _AisleRecord(passenger, entry_cell, door)
            in_aisle[passenger.id] = record
            current_occupancy[entry_cell] = record
            if first_entry_time is None:
                first_entry_time = time_seconds
            events.append(
                SimulationEvent(
                    "aircraft_entered",
                    time_seconds,
                    passenger.id,
                    {"door": door, "entryCell": entry_cell},
                )
            )

        simultaneous_aisle_seat_violations += sum(
            passenger.seated and passenger.id in in_aisle
            for passenger in passengers
        )

        time_seconds += dt
        while time_seconds + 1e-9 >= next_sample_time:
            history.append(
                _snapshot(
                    passengers,
                    access,
                    next_sample_time,
                    len(entered),
                    seated_count,
                )
            )
            next_sample_time += sample_seconds

    timed_out = seated_count < total
    if history[-1].time_seconds != time_seconds:
        history.append(
            _snapshot(passengers, access, time_seconds, len(entered), seated_count)
        )
    cabin_seconds = (
        None
        if first_entry_time is None or last_seat_time is None
        else last_seat_time - first_entry_time
    )
    aircraft_phase_seconds = (
        config["maxBoardingSeconds"]
        if last_seat_time is None
        else last_seat_time - first_ready
    )
    return AircraftResult(
        history=history,
        events=events,
        movement_audit=movement_audit,
        first_aircraft_ready_time=first_ready,
        first_entry_time=first_entry_time,
        last_seat_time=last_seat_time,
        cabin_boarding_seconds=cabin_seconds,
        aircraft_phase_seconds=aircraft_phase_seconds,
        seated_count=seated_count,
        timed_out=timed_out,
        diagnostics={
            "aisleCells": aisle_cell_count,
            "maxAisleOccupancy": max_aisle_occupancy,
            "conflictCount": conflict_count,
            "occupiedSeatCount": len(occupied_seats),
            "occupancyViolations": occupancy_violations,
            "simultaneousAisleSeatViolations": simultaneous_aisle_seat_violations,
            "duplicateSeatCount": duplicate_seat_count,
            "minimumServiceRemaining": minimum_service_remaining or 0.0,
            "movementEventCount": len(movement_audit),
        },
    )
