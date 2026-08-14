"""Compact authoritative replay assembly for the public browser experience."""

from __future__ import annotations

from typing import Any

from .models import AircraftResult, Passenger, PreparationResult


REPLAY_STATE_CODES = {
    "gate_waiting": 0,
    "gate_moving": 1,
    "gate_correcting": 2,
    "gate_staged": 3,
    "access_waiting": 4,
    "access_moving": 5,
    "aircraft_queue": 6,
    "aisle_moving": 7,
    "row_service": 8,
    "seated": 9,
}

EVENT_CODES = {
    "aircraft_entered": 0,
    "aisle_moved": 1,
    "row_service_started": 2,
    "seated": 3,
}


def _state_code(state: str) -> int:
    if state in {"waiting", "standing"}:
        return REPLAY_STATE_CODES["gate_waiting"]
    if state == "moving":
        return REPLAY_STATE_CODES["gate_moving"]
    if state == "correcting":
        return REPLAY_STATE_CODES["gate_correcting"]
    if state == "staged":
        return REPLAY_STATE_CODES["gate_staged"]
    if state in {"door_queue", "approaching_door"}:
        return REPLAY_STATE_CODES["aircraft_queue"]
    if state == "aisle_moving":
        return REPLAY_STATE_CODES["aisle_moving"]
    if state == "row_service":
        return REPLAY_STATE_CODES["row_service"]
    if state == "seated":
        return REPLAY_STATE_CODES["seated"]
    if "waiting" in state or state == "at_gate":
        return REPLAY_STATE_CODES["access_waiting"]
    return REPLAY_STATE_CODES["access_moving"]


def _gate_frames(preparation: PreparationResult) -> list[list[Any]]:
    return [
        [
            frame.time_seconds,
            frame.mean_frustration,
            frame.mean_accumulated_burden,
            [
                [
                    state.passenger_id,
                    state.x_m,
                    state.y_m,
                    state.frustration,
                    state.frustration_burden,
                    _state_code(state.state),
                ]
                for state in frame.passengers
            ],
        ]
        for frame in preparation.gate_replay.frames
    ]


def _frustration_frames(
    preparation: PreparationResult, aircraft: AircraftResult
) -> list[list[Any]]:
    frames = [
        [
            frame.time_seconds,
            frame.mean_frustration,
            frame.mean_accumulated_burden,
            [
                [
                    state.passenger_id,
                    state.frustration,
                    state.frustration_burden,
                    _state_code(state.state),
                ]
                for state in frame.passengers
            ],
        ]
        for frame in preparation.gate_replay.frames
    ]
    for time_seconds, mean_frustration, mean_burden, states in aircraft.frustration_frames:
        if frames and time_seconds <= frames[-1][0]:
            continue
        frames.append(
            [
                time_seconds,
                mean_frustration,
                mean_burden,
                [
                    [passenger_id, frustration, burden, _state_code(state)]
                    for passenger_id, frustration, burden, state in states
                ],
            ]
        )
    return frames


def _aircraft_events(aircraft: AircraftResult) -> list[list[Any]]:
    events: list[list[Any]] = []
    for event in aircraft.events:
        if event.type not in EVENT_CODES:
            continue
        details = event.details
        if event.type == "aircraft_entered":
            tail = [details.get("door"), details.get("entryCell")]
        elif event.type == "row_service_started":
            tail = [details.get("targetCell"), details.get("durationSeconds")]
        elif event.type == "seated":
            tail = [details.get("row"), details.get("seat")]
        else:
            tail = []
        events.append(
            [event.time_seconds, EVENT_CODES[event.type], event.passenger_id, *tail]
        )
    events.extend(
        [
            event.time_seconds,
            EVENT_CODES["aisle_moved"],
            event.passenger_id,
            event.door,
            event.from_cell,
            event.to_cell,
            event.target_cell,
        ]
        for event in aircraft.movement_audit
    )
    return sorted(events, key=lambda event: (event[0], event[1], event[2]))


def build_replay(
    passengers: list[Passenger],
    preparation: PreparationResult,
    aircraft: AircraftResult,
) -> dict[str, Any]:
    end_time = (
        aircraft.last_seat_time
        if aircraft.last_seat_time is not None
        else aircraft.frustration_frames[-1][0]
    )
    return {
        "starts_at_seconds": 0,
        "ends_at_seconds": end_time,
        "state_codebook": dict(REPLAY_STATE_CODES),
        "event_codebook": dict(EVENT_CODES),
        "driver_labels": [
            "instruction_complexity",
            "correction",
            "waiting",
            "crowding",
            "aisle_blocked",
            "row_service",
            "visible_progress",
        ],
        "gate": {
            "layout": preparation.gate_replay.layout,
            "slots": [
                [
                    slot.passenger_id,
                    slot.slot_index,
                    slot.cohort,
                    slot.point.x_m,
                    slot.point.y_m,
                ]
                for slot in preparation.gate_replay.slots
            ],
            "frames": _gate_frames(preparation),
        },
        "frustration_frames": _frustration_frames(preparation, aircraft),
        "aircraft_events": _aircraft_events(aircraft),
        "passenger_tracks": {
            str(passenger.id): [
                passenger.row,
                passenger.seat,
                passenger.family_id,
                passenger.boarding_rank,
                passenger.assigned_door,
            ]
            for passenger in passengers
        },
    }
