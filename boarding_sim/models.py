"""Typed internal model records shared by simulation modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Passenger:
    id: int
    row: int
    seat: str
    family_id: int
    tolerance_threshold: float
    delay_sensitivity: float
    uncertainty_sensitivity: float
    wait_sensitivity: float
    crowd_sensitivity: float
    social_susceptibility: float
    compliance: float
    information_trust: float
    fatigue: float
    connection_pressure: float
    urgency: float
    walking_speed_mps: float
    bag_count: int
    stress_load: float = 0.0
    initial_stress_load: float = 0.0
    frustration: float = 0.0
    initial_frustration: float = 0.0
    frustration_burden: float = 0.0
    preparation_frustration_burden: float = 0.0
    embarkation_frustration_burden: float = 0.0
    peak_frustration: float = 0.0
    time_above_threshold_seconds: float = 0.0
    prep_state: str = "waiting"
    prep_correct: bool = False
    correction_count: int = 0
    prep_distance_m: float = 0.0
    move_remaining_s: float = 0.0
    correct_remaining_s: float = 0.0
    blocked_seconds: float = 0.0
    raw_cohort: int = 0
    random_key: float = 0.0
    raw_rank: float = 0.0
    assigned_door: str = "front"
    prep_cohort: int = 0
    boarding_rank: float = 0.0
    companion_override: bool = False
    access_state: str = "at_gate"
    aircraft_state: str = "not_arrived"
    seated: bool = False


@dataclass(frozen=True)
class SimulationEvent:
    type: str
    time_seconds: float
    passenger_id: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProgressSample:
    time_seconds: float
    phase: str
    mean_frustration: float
    p90_frustration: float
    prepared_count: int
    access_arrived_count: int
    entered_count: int
    seated_count: int


@dataclass(frozen=True)
class ReadinessState:
    overall: float
    first_cohort: float
    ready: bool


@dataclass(frozen=True)
class GatePoint:
    x_m: float
    y_m: float


@dataclass(frozen=True)
class QueueSlot:
    passenger_id: int
    slot_index: int
    cohort: int
    point: GatePoint


@dataclass(frozen=True)
class GateLayout:
    width_m: float
    height_m: float
    boarding_control: GatePoint


@dataclass
class GatePlan:
    layout: GateLayout
    start_positions: dict[int, GatePoint]
    slots: list[QueueSlot]
    queue_slots: dict[int, GatePoint]


@dataclass(frozen=True)
class GatePassengerState:
    passenger_id: int
    x_m: float
    y_m: float
    state: str
    frustration: float
    frustration_burden: float


@dataclass(frozen=True)
class GateFrame:
    time_seconds: float
    mean_frustration: float
    mean_accumulated_burden: float
    passengers: list[GatePassengerState]


@dataclass
class GateReplay:
    layout: GateLayout
    slots: list[QueueSlot]
    frames: list[GateFrame]


@dataclass
class PreparationResult:
    time_seconds: float
    history: list[ProgressSample]
    events: list[SimulationEvent]
    corrections: int
    readiness: ReadinessState
    complexity: float
    timed_out: bool
    gate_replay: GateReplay


@dataclass(frozen=True)
class AircraftArrival:
    passenger_id: int
    door: str
    ready_time: float


@dataclass(frozen=True)
class AccessSegment:
    start_time: float
    end_time: float
    state: str


@dataclass
class AccessResult:
    mode: str
    arrivals: list[AircraftArrival]
    transfer_end_seconds: float
    history: list[ProgressSample]
    events: list[SimulationEvent]
    buses: list[dict[str, Any]] = field(default_factory=list)
    passenger_segments: dict[int, list[AccessSegment]] = field(default_factory=dict)


@dataclass(frozen=True)
class MovementEvent:
    time_seconds: float
    passenger_id: int
    door: str
    from_cell: int
    to_cell: int
    target_cell: int


@dataclass
class AircraftResult:
    history: list[ProgressSample]
    events: list[SimulationEvent]
    movement_audit: list[MovementEvent]
    frustration_frames: list[list[Any]]
    first_aircraft_ready_time: float
    first_entry_time: float | None
    last_seat_time: float | None
    cabin_boarding_seconds: float | None
    aircraft_phase_seconds: float
    seated_count: int
    timed_out: bool
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class DistributionSummary:
    count: int
    minimum: float
    p10: float
    p50: float
    mean: float
    p90: float
    p95: float
    maximum: float
    mean_ci95_low: float
    mean_ci95_high: float


@dataclass
class FlightResult:
    schema_version: str
    model_version: str
    seed: int
    status: str
    model_status: dict[str, Any]
    scenario: dict[str, Any]
    strategy: dict[str, Any]
    parameter_provenance: list[dict[str, Any]]
    passengers: list[Passenger]
    phases: dict[str, Any]
    replay: dict[str, Any]
    trajectory: list[ProgressSample]
    metrics: dict[str, Any]
    diagnostics: dict[str, Any]
