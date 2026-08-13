"""Event-based bridge and bus access scheduling."""

from __future__ import annotations

from typing import Any

from .models import (
    AccessResult,
    AccessSegment,
    AircraftArrival,
    Passenger,
    ProgressSample,
    SimulationEvent,
)
from .prng import RNG
from .stats import mean, quantile


def _boarding_order(passengers: list[Passenger]) -> list[Passenger]:
    return sorted(passengers, key=lambda passenger: (passenger.boarding_rank, passenger.id))


def _append_segment(
    schedules: dict[int, list[AccessSegment]],
    passenger_id: int,
    start_time: float,
    end_time: float,
    state: str,
) -> None:
    if end_time > start_time:
        schedules.setdefault(passenger_id, []).append(
            AccessSegment(start_time, end_time, state)
        )


def _history(
    passengers: list[Passenger],
    arrivals: list[AircraftArrival],
    start_time: float,
    end_time: float,
    scenario: dict[str, Any],
    mode: str,
) -> list[ProgressSample]:
    sample_seconds = scenario["metrics"]["historySampleSeconds"]
    times: list[float] = [start_time]
    next_time = start_time + sample_seconds
    while next_time < end_time:
        times.append(next_time)
        next_time += sample_seconds
    if end_time != start_time:
        times.append(end_time)
    frustrations = [passenger.frustration for passenger in passengers]
    return [
        ProgressSample(
            time_seconds=time_seconds,
            phase=f"access_{mode}",
            mean_frustration=mean(frustrations),
            p90_frustration=quantile(frustrations, 0.9),
            prepared_count=sum(passenger.prep_correct for passenger in passengers),
            access_arrived_count=sum(
                arrival.ready_time <= time_seconds for arrival in arrivals
            ),
            entered_count=0,
            seated_count=0,
        )
        for time_seconds in times
    ]


def simulate_bridge_access(
    passengers: list[Passenger],
    scenario: dict[str, Any],
    rng: RNG,
    phase_start_seconds: float,
) -> AccessResult:
    config = scenario["access"]
    queue = _boarding_order(passengers)
    events: list[SimulationEvent] = []
    schedules: dict[int, list[AccessSegment]] = {}
    arrivals: list[AircraftArrival] = []
    scan_available = phase_start_seconds
    last_door_time = phase_start_seconds
    for passenger in queue:
        scan_start = scan_available
        scan_duration = max(
            0.35,
            rng.exponential(config["gateScanMeanSeconds"] / 2.0)
            + rng.exponential(config["gateScanMeanSeconds"] / 2.0),
        )
        scan_done = scan_start + scan_duration
        scan_available = scan_done
        walk_duration = config["bridgeLengthM"] / max(
            0.5,
            min(
                config["bridgeWalkSpeedMps"], passenger.walking_speed_mps + 0.3
            ),
        )
        walk_done = scan_done + walk_duration
        ready_time = max(
            walk_done, last_door_time + config["bridgeMinimumHeadwaySeconds"]
        )
        last_door_time = ready_time
        _append_segment(schedules, passenger.id, phase_start_seconds, scan_start, "bridge_waiting")
        _append_segment(schedules, passenger.id, scan_start, scan_done, "bridge_scan")
        _append_segment(schedules, passenger.id, scan_done, walk_done, "bridge_walking")
        _append_segment(schedules, passenger.id, walk_done, ready_time, "bridge_headway_wait")
        events.extend(
            [
                SimulationEvent("boarding_control_complete", scan_done, passenger.id),
                SimulationEvent("bridge_walk_complete", walk_done, passenger.id),
                SimulationEvent(
                    "aircraft_door_arrival",
                    ready_time,
                    passenger.id,
                    {"door": passenger.assigned_door},
                ),
            ]
        )
        arrivals.append(
            AircraftArrival(passenger.id, passenger.assigned_door, ready_time)
        )
    arrivals.sort(key=lambda arrival: (arrival.ready_time, arrival.passenger_id))
    history = _history(
        passengers,
        arrivals,
        phase_start_seconds,
        last_door_time,
        scenario,
        "bridge",
    )
    return AccessResult(
        mode="bridge",
        arrivals=arrivals,
        transfer_end_seconds=last_door_time,
        history=history,
        events=sorted(events, key=lambda event: (event.time_seconds, event.type, event.passenger_id or -1)),
        passenger_segments=schedules,
    )


def simulate_bus_access(
    passengers: list[Passenger],
    scenario: dict[str, Any],
    rng: RNG,
    phase_start_seconds: float,
) -> AccessResult:
    config = scenario["access"]
    queue = _boarding_order(passengers)
    buses: list[dict[str, Any]] = [
        {
            "id": bus_id,
            "records": [],
            "readyAt": phase_start_seconds,
            "departAt": None,
            "arriveAt": None,
        }
        for bus_id in range(int(config["busCount"]))
    ]
    events: list[SimulationEvent] = []
    schedules: dict[int, list[AccessSegment]] = {}
    for passenger in queue:
        eligible = [
            bus
            for bus in buses
            if len(bus["records"]) < int(config["busCapacity"])
        ]
        if not eligible:
            raise ValueError("Bus capacity is insufficient for passenger count.")
        bus = min(eligible, key=lambda item: (item["readyAt"], item["id"]))
        load_start = max(phase_start_seconds, bus["readyAt"])
        load_done = load_start + max(
            0.35, rng.exponential(config["busBoardMeanSeconds"])
        )
        record = {
            "passenger": passenger,
            "loadStart": load_start,
            "loadedAt": load_done,
            "unloadedAt": None,
        }
        bus["records"].append(record)
        bus["readyAt"] = load_done
        events.append(
            SimulationEvent("bus_loaded", load_done, passenger.id, {"busId": bus["id"]})
        )

    for bus in buses:
        if not bus["records"]:
            continue
        bus["departAt"] = bus["readyAt"]
        bus["arriveAt"] = bus["departAt"] + max(
            30.0,
            rng.normal(
                config["busTravelMeanSeconds"], config["busTravelSdSeconds"]
            ),
        )
        events.append(SimulationEvent("bus_departed", bus["departAt"], details={"busId": bus["id"]}))
        events.append(SimulationEvent("bus_arrived", bus["arriveAt"], details={"busId": bus["id"]}))

    arrivals: list[AircraftArrival] = []
    for bus in buses:
        if not bus["records"]:
            continue
        door_streams: dict[str, list[dict[str, Any]]] = {"front": [], "rear": []}
        for record in bus["records"]:
            door_streams[record["passenger"].assigned_door].append(record)
        for door in ("front", "rear"):
            unload_time = bus["arriveAt"]
            for record in door_streams[door]:
                passenger = record["passenger"]
                unload_time += max(
                    0.25, rng.exponential(config["busUnloadMeanSeconds"])
                )
                record["unloadedAt"] = unload_time
                _append_segment(schedules, passenger.id, phase_start_seconds, record["loadStart"], "bus_gate_waiting")
                _append_segment(schedules, passenger.id, record["loadStart"], record["loadedAt"], "bus_loading")
                _append_segment(schedules, passenger.id, record["loadedAt"], bus["departAt"], "bus_onboard_waiting")
                _append_segment(schedules, passenger.id, bus["departAt"], bus["arriveAt"], "bus_travelling")
                _append_segment(schedules, passenger.id, bus["arriveAt"], unload_time, "bus_unloading")
                events.extend(
                    [
                        SimulationEvent("bus_unloaded", unload_time, passenger.id, {"busId": bus["id"], "door": door}),
                        SimulationEvent("aircraft_door_arrival", unload_time, passenger.id, {"door": door}),
                    ]
                )
                arrivals.append(AircraftArrival(passenger.id, door, unload_time))

    arrivals.sort(key=lambda arrival: (arrival.ready_time, arrival.passenger_id))
    end_time = max(arrival.ready_time for arrival in arrivals)
    public_buses = [
        {
            "id": bus["id"],
            "passengerCount": len(bus["records"]),
            "departAt": bus["departAt"],
            "arriveAt": bus["arriveAt"],
        }
        for bus in buses
        if bus["records"]
    ]
    return AccessResult(
        mode="bus",
        arrivals=arrivals,
        transfer_end_seconds=end_time,
        history=_history(passengers, arrivals, phase_start_seconds, end_time, scenario, "bus"),
        events=sorted(events, key=lambda event: (event.time_seconds, event.type, event.passenger_id or -1)),
        buses=public_buses,
        passenger_segments=schedules,
    )


def simulate_access(
    passengers: list[Passenger],
    scenario: dict[str, Any],
    rng: RNG,
    calibration: dict[str, Any],
    phase_start_seconds: float,
) -> AccessResult:
    del calibration  # Access stress is integrated synchronously by the aircraft phase.
    if scenario["access"]["mode"] == "bus":
        return simulate_bus_access(passengers, scenario, rng, phase_start_seconds)
    return simulate_bridge_access(passengers, scenario, rng, phase_start_seconds)


def access_rates(
    passenger: Passenger,
    state: str,
    calibration: dict[str, Any],
) -> tuple[float, float]:
    coefficients = calibration["transferPerMinute"]
    if state in {"bridge_waiting", "bridge_scan", "bridge_headway_wait"}:
        return coefficients["bridgeWaiting"] * passenger.wait_sensitivity, 0.0
    if state == "bridge_walking":
        return 0.0, coefficients["bridgeWalkingRecovery"]
    if state in {"bus_gate_waiting", "bus_loading"}:
        return coefficients["busWaiting"] * passenger.wait_sensitivity, 0.0
    if state == "bus_onboard_waiting":
        return (
            coefficients["busWaiting"] * passenger.wait_sensitivity
            + coefficients["busCrowding"] * passenger.crowd_sensitivity,
            0.0,
        )
    if state == "bus_travelling":
        return (
            coefficients["busCrowding"] * 0.35 * passenger.crowd_sensitivity,
            coefficients["busMovingRecovery"],
        )
    if state == "bus_unloading":
        return 0.0, coefficients["unloadingRecovery"]
    return 0.0, 0.0


def access_state_at(result: AccessResult, passenger_id: int, time_seconds: float) -> str | None:
    for segment in result.passenger_segments.get(passenger_id, []):
        if segment.start_time <= time_seconds < segment.end_time:
            return segment.state
    return None
