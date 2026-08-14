"""Agent-based gate preparation with explicit readiness policies."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

from .frustration import clamp, evolve_passenger, frustration_from_load, logistic
from .gate import build_gate_plan
from .models import (
    GateFrame,
    GatePassengerState,
    GatePlan,
    GatePoint,
    GateReplay,
    Passenger,
    PreparationResult,
    ProgressSample,
    ReadinessState,
    SimulationEvent,
)
from .prng import RNG
from .stats import mean, quantile
from .strategies import Strategy, strategy_complexity


class PreparationPolicy(Protocol):
    mode: str

    def evaluate(self, passengers: list[Passenger]) -> ReadinessState: ...


@dataclass(frozen=True)
class StrictPreparationPolicy:
    readiness_target: float
    first_cohort_target: float
    mode: str = "strict_preparation"

    def evaluate(self, passengers: list[Passenger]) -> ReadinessState:
        overall = sum(passenger.prep_correct for passenger in passengers) / max(1, len(passengers))
        first_cohort = min(passenger.prep_cohort for passenger in passengers)
        members = [passenger for passenger in passengers if passenger.prep_cohort == first_cohort]
        first_ready = sum(passenger.prep_correct for passenger in members) / max(1, len(members))
        return ReadinessState(
            overall=overall,
            first_cohort=first_ready,
            ready=overall >= self.readiness_target and first_ready >= self.first_cohort_target,
        )


@dataclass(frozen=True)
class CompletePreparationPolicy:
    mode: str = "complete_preparation"

    def evaluate(self, passengers: list[Passenger]) -> ReadinessState:
        overall = sum(passenger.prep_correct for passenger in passengers) / max(
            1, len(passengers)
        )
        first_cohort = min(passenger.prep_cohort for passenger in passengers)
        members = [
            passenger
            for passenger in passengers
            if passenger.prep_cohort == first_cohort
        ]
        first_ready = sum(passenger.prep_correct for passenger in members) / max(
            1, len(members)
        )
        return ReadinessState(overall, first_ready, overall == 1.0)


def readiness_policy_from_config(config: dict[str, Any]) -> PreparationPolicy:
    if config["mode"] == "strict_preparation":
        return StrictPreparationPolicy(
            readiness_target=config["readinessTarget"],
            first_cohort_target=config["firstCohortTarget"],
        )
    if config["mode"] == "complete_preparation":
        return CompletePreparationPolicy()
    raise ValueError(f"Unsupported preparation policy {config['mode']}")


def apply_companion_separation_shock(
    passengers: list[Passenger],
    strategy: Strategy,
    calibration: dict[str, Any],
) -> list[SimulationEvent]:
    """Apply the provisional stress cost of a strategy-enforced family split."""
    if strategy.companion_policy != "separate":
        return []
    shock = calibration["companionSeparationShock"]
    events: list[SimulationEvent] = []
    for passenger in passengers:
        if not passenger.family_id or not passenger.companion_override:
            continue
        passenger.stress_load = clamp(passenger.stress_load + shock, 0.0, 2.0)
        passenger.frustration = frustration_from_load(passenger, calibration)
        passenger.peak_frustration = max(
            passenger.peak_frustration, passenger.frustration
        )
        events.append(
            SimulationEvent(
                "companion_separation_shock",
                0.0,
                passenger.id,
                {"stress_load_shock": shock},
            )
        )
    return events


def _groups(passengers: list[Passenger]) -> dict[int, list[Passenger]]:
    groups: dict[int, list[Passenger]] = {}
    for passenger in passengers:
        if passenger.family_id:
            groups.setdefault(passenger.family_id, []).append(passenger)
    return groups


def _snapshot(passengers: list[Passenger], time_seconds: float) -> ProgressSample:
    frustrations = [passenger.frustration for passenger in passengers]
    return ProgressSample(
        time_seconds=time_seconds,
        phase="preparation",
        mean_frustration=mean(frustrations),
        p90_frustration=quantile(frustrations, 0.9),
        prepared_count=sum(passenger.prep_correct for passenger in passengers),
        access_arrived_count=0,
        entered_count=0,
        seated_count=0,
    )


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _gate_frame(
    passengers: list[Passenger],
    positions: dict[int, tuple[float, float]],
    time_seconds: float,
) -> GateFrame:
    return GateFrame(
        time_seconds=time_seconds,
        mean_frustration=mean(passenger.frustration for passenger in passengers),
        mean_accumulated_burden=mean(
            passenger.frustration_burden for passenger in passengers
        ),
        passengers=[
            GatePassengerState(
                passenger_id=passenger.id,
                x_m=round(positions[passenger.id][0], 3),
                y_m=round(positions[passenger.id][1], 3),
                state=passenger.prep_state,
                frustration=round(passenger.frustration, 6),
                frustration_burden=round(passenger.frustration_burden, 6),
            )
            for passenger in sorted(passengers, key=lambda item: item.id)
        ],
    )


def _advance_gate_positions(
    passengers: list[Passenger],
    positions: dict[int, tuple[float, float]],
    targets: dict[int, GatePoint],
    dt: float,
    gate_density: float,
    collision_tolerance: float,
    rng: RNG,
) -> None:
    passenger_by_id = {passenger.id: passenger for passenger in passengers}
    moving_ids = [
        passenger.id for passenger in passengers if passenger.prep_state == "moving"
    ]
    rng.shuffle(moving_ids)
    protected = dict(positions)
    for passenger_id in moving_ids:
        passenger = passenger_by_id[passenger_id]
        current = positions[passenger_id]
        target_point = targets[passenger_id]
        target = (target_point.x_m, target_point.y_m)
        remaining = _distance(current, target)
        if remaining <= 1e-9:
            positions[passenger_id] = target
            continue
        speed = passenger.walking_speed_mps / (
            1.0 + 1.8 * gate_density * gate_density
        )
        step = min(remaining, speed * dt)
        ratio = step / remaining
        proposed = (
            current[0] + (target[0] - current[0]) * ratio,
            current[1] + (target[1] - current[1]) * ratio,
        )
        protected.pop(passenger_id, None)
        blocked = any(
            _distance(proposed, other) < collision_tolerance
            for other in protected.values()
        )
        accepted = current if blocked else proposed
        positions[passenger_id] = accepted
        protected[passenger_id] = accepted


def simulate_preparation(
    passengers: list[Passenger],
    scenario: dict[str, Any],
    strategy: Strategy,
    rng: RNG,
    calibration: dict[str, Any],
    gate_plan: GatePlan | None = None,
) -> PreparationResult:
    config = scenario["preparation"]
    threshold = scenario["metrics"]["frustrationThreshold"]
    sample_seconds = scenario["metrics"]["historySampleSeconds"]
    coefficients = calibration["preparationPerMinute"]
    decision = calibration["decision"]
    policy = readiness_policy_from_config(config["policy"])
    complexity = strategy_complexity(strategy)
    families = _groups(passengers)
    events = apply_companion_separation_shock(passengers, strategy, calibration)
    history = [_snapshot(passengers, 0.0)]
    total_corrections = 0
    time_seconds = 0.0
    dt = 1.0
    plan = gate_plan or build_gate_plan(
        passengers, scenario, strategy, rng.fork(811)
    )
    movement_rng = rng.fork(812)
    positions = {
        passenger_id: (point.x_m, point.y_m)
        for passenger_id, point in plan.start_positions.items()
    }
    collision_tolerance = 0.005
    replay_sample_seconds = float(config["replaySampleSeconds"])

    for passenger in passengers:
        stand_probability = clamp(
            0.06
            + 0.24 * passenger.urgency
            + 0.18 * passenger.frustration
            + 0.08 * passenger.social_susceptibility,
            0.02,
            0.65,
        )
        passenger.prep_state = "standing" if rng.boolean(stand_probability) else "waiting"
        passenger.prep_correct = False
        target = plan.queue_slots[passenger.id]
        passenger.prep_distance_m = _distance(
            positions[passenger.id], (target.x_m, target.y_m)
        )
        passenger.move_remaining_s = 0.0
        passenger.correct_remaining_s = 0.0

    gate_frames = [_gate_frame(passengers, positions, 0.0)]

    while time_seconds < config["maxPreparationSeconds"]:
        events_before_step = len(events)
        staged_count = sum(passenger.prep_state == "staged" for passenger in passengers)
        moving_count = sum(passenger.prep_state in {"moving", "correcting"} for passenger in passengers)
        standing_count = sum(passenger.prep_state != "waiting" for passenger in passengers)
        gate_density = clamp(
            (staged_count + moving_count) / max(1.0, config["gateUsableAreaM2"]),
            0.0,
            1.6,
        )
        social_signal = standing_count / len(passengers)
        visible_progress = staged_count / len(passengers)
        staged_frustrations = [
            passenger.frustration
            for passenger in passengers
            if passenger.prep_state == "staged"
        ]
        staged_mean_frustration = mean(staged_frustrations or [passenger.frustration for passenger in passengers])
        _advance_gate_positions(
            passengers,
            positions,
            plan.queue_slots,
            dt,
            gate_density,
            collision_tolerance,
            movement_rng,
        )

        for passenger in passengers:
            if passenger.prep_state == "staged":
                social_load = (
                    coefficients["socialCoupling"]
                    * passenger.social_susceptibility
                    * (staged_mean_frustration - passenger.frustration)
                )
                evolve_passenger(
                    passenger,
                    dt,
                    coefficients["uncertainty"]
                    * passenger.uncertainty_sensitivity
                    * (1.0 - visible_progress)
                    + max(0.0, social_load),
                    coefficients["visibleProgressRecovery"] * visible_progress
                    + max(0.0, -social_load),
                    calibration,
                    threshold,
                )
                continue

            if passenger.prep_state == "correcting":
                passenger.correct_remaining_s -= dt
                evolve_passenger(
                    passenger,
                    dt,
                    coefficients["instruction"] * complexity * (1.0 - passenger.compliance)
                    + coefficients["correctionShock"],
                    0.0,
                    calibration,
                    threshold,
                )
                if passenger.correct_remaining_s <= 0:
                    passenger.correct_remaining_s = 0.0
                    passenger.prep_state = "staged"
                    passenger.prep_correct = True
                    events.append(SimulationEvent("preparation_corrected", time_seconds, passenger.id))
                continue

            if passenger.prep_state == "moving":
                evolve_passenger(
                    passenger,
                    dt,
                    coefficients["crowding"] * passenger.crowd_sensitivity * gate_density
                    + coefficients["instruction"] * complexity * 0.35,
                    coefficients["visibleProgressRecovery"] * 0.45,
                    calibration,
                    threshold,
                )
                target = plan.queue_slots[passenger.id]
                if _distance(
                    positions[passenger.id], (target.x_m, target.y_m)
                ) <= 1e-9:
                    passenger.move_remaining_s = 0.0
                    correct_probability = clamp(
                        0.985
                        - 0.42 * complexity * (1.0 - passenger.compliance)
                        - 0.14 * complexity * (1.0 - passenger.information_trust),
                        0.45,
                        0.995,
                    )
                    if rng.boolean(correct_probability):
                        passenger.prep_state = "staged"
                        passenger.prep_correct = True
                        events.append(SimulationEvent("preparation_staged", time_seconds, passenger.id))
                    else:
                        passenger.prep_state = "correcting"
                        passenger.correction_count += 1
                        total_corrections += 1
                        passenger.correct_remaining_s = (
                            8.0 + 18.0 * complexity + rng.triangular(3.0, 8.0, 18.0)
                        )
                        events.append(
                            SimulationEvent(
                                "preparation_correction",
                                time_seconds,
                                passenger.id,
                                {"cohort": passenger.prep_cohort},
                            )
                        )
                continue

            family = families.get(passenger.family_id) if passenger.family_id else None
            family_active = bool(
                family
                and any(
                    member.prep_state in {"moving", "correcting", "staged"}
                    for member in family
                )
            )
            no_progress = 1.0 - visible_progress
            load_rate = (
                coefficients["uncertainty"]
                * passenger.uncertainty_sensitivity
                * no_progress
                + coefficients["noProgress"] * passenger.wait_sensitivity * no_progress
                + coefficients["crowding"] * passenger.crowd_sensitivity * gate_density
                + coefficients["instruction"] * complexity * 0.25
            )
            recovery = coefficients["seatedRecovery"] if passenger.prep_state == "waiting" else 0.0
            evolve_passenger(
                passenger, dt, load_rate, recovery, calibration, threshold
            )
            utility = (
                decision["activationBase"]
                + decision["frustration"] * passenger.frustration
                + decision["urgency"] * passenger.urgency
                + decision["social"]
                * passenger.social_susceptibility
                * social_signal
                + decision["family"] * (1.0 if family_active else 0.0)
                + decision["progress"] * visible_progress
                - decision["complexityPenalty"]
                * complexity
                * (1.0 - passenger.compliance)
            )
            per_second = 1.0 - (1.0 - logistic(utility)) ** (dt / 5.0)
            if rng.boolean(per_second):
                passenger.prep_state = "moving"
                family_slowdown = 1.0
                if family:
                    family_slowdown = (
                        max(1.0 / max(0.4, member.walking_speed_mps) for member in family)
                        * passenger.walking_speed_mps
                    )
                passenger.move_remaining_s = (
                    passenger.prep_distance_m / max(0.35, passenger.walking_speed_mps)
                ) * family_slowdown
                events.append(SimulationEvent("preparation_started", time_seconds, passenger.id))
            elif passenger.prep_state == "waiting" and rng.boolean(
                0.05 + 0.15 * passenger.frustration
            ):
                passenger.prep_state = "standing"

        time_seconds += dt
        if time_seconds % sample_seconds == 0:
            history.append(_snapshot(passengers, time_seconds))
        readiness = policy.evaluate(passengers)
        should_record_gate = (
            time_seconds % replay_sample_seconds == 0
            or len(events) != events_before_step
            or readiness.ready
        )
        if should_record_gate and gate_frames[-1].time_seconds != time_seconds:
            gate_frames.append(_gate_frame(passengers, positions, time_seconds))
        if readiness.ready:
            if history[-1].time_seconds != time_seconds:
                history.append(_snapshot(passengers, time_seconds))
            return PreparationResult(
                time_seconds,
                history,
                events,
                total_corrections,
                readiness,
                complexity,
                False,
                GateReplay(plan.layout, plan.slots, gate_frames),
            )

    readiness = policy.evaluate(passengers)
    if history[-1].time_seconds != time_seconds:
        history.append(_snapshot(passengers, time_seconds))
    if gate_frames[-1].time_seconds != time_seconds:
        gate_frames.append(_gate_frame(passengers, positions, time_seconds))
    return PreparationResult(
        time_seconds,
        history,
        events,
        total_corrections,
        readiness,
        complexity,
        True,
        GateReplay(plan.layout, plan.slots, gate_frames),
    )
