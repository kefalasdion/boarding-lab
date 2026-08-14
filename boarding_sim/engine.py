"""Public single-flight simulation orchestration."""

from __future__ import annotations

import copy
from typing import Any

from .access import simulate_access
from .aircraft import simulate_aircraft
from .metrics import (
    build_metrics,
    build_preparation_timeout_metrics,
    summarize_distribution,
)
from .models import FlightResult, Passenger
from .population import assign_strategy, generate_manifest
from .preparation import simulate_preparation
from .prng import RNG
from .provenance import load_parameter_registry, validate_registry_coverage
from .replay import build_preparation_only_replay, build_replay
from .strategies import Strategy, strategy_by_id
from .validation import (
    load_behaviour_calibration,
    load_default_scenario,
    normalize_scenario,
    validate_seed,
)

SCHEMA_VERSION = "1.1.0"
MODEL_VERSION = "pbs-v2-python-1.1.0"

MODEL_STATUS = {
    "application": "research_and_calibration_tool",
    "aircraft_core_basis": "published_field_and_literature_model_inputs",
    "preparation_calibrated": False,
    "frustration_validated": False,
    "operational_claims_allowed": False,
    "warning": "Frustration outputs are provisional until Validation Plan Layer 4 passes.",
}


def _model_inputs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calibration = load_behaviour_calibration()
    registry = load_parameter_registry()
    coverage_issues = validate_registry_coverage(
        load_default_scenario(), calibration, registry
    )
    if coverage_issues:
        raise RuntimeError("Parameter registry is invalid: " + "; ".join(coverage_issues))
    return calibration, registry


def _strategy_description(strategy: Strategy) -> dict[str, Any]:
    return {
        "id": strategy.id,
        "name": strategy.name,
        "recommended_access": strategy.access_recommended,
        "preparation_cohorts": strategy.prep_cohorts,
    }


def _part1(passengers: list[Passenger]) -> dict[str, Any]:
    return {
        "time_seconds": 0,
        "passenger_count": len(passengers),
        "initial_frustration": summarize_distribution(
            passenger.initial_frustration for passenger in passengers
        ),
        "tolerance_threshold": summarize_distribution(
            passenger.tolerance_threshold for passenger in passengers
        ),
        "latent_stress_load": summarize_distribution(
            passenger.initial_stress_load for passenger in passengers
        ),
    }


def _part2(scenario: dict[str, Any], preparation: Any) -> dict[str, Any]:
    return {
        "policy": scenario["preparation"]["policy"],
        "duration_seconds": preparation.time_seconds,
        "timed_out": preparation.timed_out,
        "readiness": preparation.readiness,
        "complexity": preparation.complexity,
        "correction_count": preparation.corrections,
        "progress": preparation.history,
        "events": preparation.events,
        "gate_replay": preparation.gate_replay,
    }


def _not_started_embarkation() -> dict[str, Any]:
    return {
        "status": "not_started",
        "duration_seconds": None,
        "access": {
            "mode": None,
            "duration_until_last_door_arrival_seconds": None,
            "last_door_arrival_time_seconds": None,
            "progress": [],
            "events": [],
            "buses": [],
        },
        "aircraft": {
            "first_door_ready_time_seconds": None,
            "first_entry_time_seconds": None,
            "last_seat_time_seconds": None,
            "cabin_boarding_seconds": None,
            "timed_out": False,
            "progress": [],
            "events": [],
            "diagnostics": {},
        },
    }


def _run_assigned_flight(
    scenario: dict[str, Any],
    validated_seed: int,
    passengers: list[Passenger],
    strategy: Strategy,
    calibration: dict[str, Any],
    registry: list[dict[str, Any]],
) -> FlightResult:
    root_rng = RNG(validated_seed)
    preparation = simulate_preparation(
        passengers, scenario, strategy, root_rng.fork(2), calibration
    )
    for passenger in passengers:
        passenger.preparation_frustration_burden = passenger.frustration_burden

    base = {
        "schema_version": SCHEMA_VERSION,
        "model_version": MODEL_VERSION,
        "seed": validated_seed,
        "model_status": dict(MODEL_STATUS),
        "scenario": scenario,
        "strategy": _strategy_description(strategy),
        "parameter_provenance": registry,
        "passengers": passengers,
    }
    if preparation.timed_out:
        return FlightResult(
            **base,
            status="timed_out",
            phases={
                "part1_t0_state": _part1(passengers),
                "part2_preparation": _part2(scenario, preparation),
                "part3_embarkation": _not_started_embarkation(),
            },
            replay=build_preparation_only_replay(passengers, preparation),
            trajectory=list(preparation.history),
            metrics=build_preparation_timeout_metrics(
                passengers, scenario, preparation
            ),
            diagnostics={
                "preparation_rng_stream": 2,
                "access_rng_stream": None,
                "aircraft_rng_stream": None,
                "movement_audit_event_count": 0,
                "deterministic_serialization": "Python JSON, sorted keys, compact separators, allow_nan=false",
            },
        )

    access = simulate_access(
        passengers,
        scenario,
        root_rng.fork(3),
        calibration,
        preparation.time_seconds,
    )
    aircraft = simulate_aircraft(
        passengers,
        access,
        scenario,
        root_rng.fork(4),
        calibration,
        preparation.time_seconds,
    )
    for passenger in passengers:
        passenger.embarkation_frustration_burden = max(
            0.0,
            passenger.frustration_burden
            - passenger.preparation_frustration_burden,
        )
    metrics = build_metrics(passengers, scenario, preparation, access, aircraft)
    replay = build_replay(passengers, preparation, aircraft)
    trajectory = list(preparation.history)
    trajectory.extend(
        sample
        for sample in aircraft.history
        if sample.time_seconds > preparation.time_seconds
    )
    return FlightResult(
        **base,
        status="timed_out" if aircraft.timed_out else "valid",
        phases={
            "part1_t0_state": _part1(passengers),
            "part2_preparation": _part2(scenario, preparation),
            "part3_embarkation": {
                "status": "complete" if not aircraft.timed_out else "timed_out",
                "duration_seconds": metrics["timings_seconds"]["embarkation"],
                "access": {
                    "mode": access.mode,
                    "duration_until_last_door_arrival_seconds": access.transfer_end_seconds
                    - preparation.time_seconds,
                    "last_door_arrival_time_seconds": access.transfer_end_seconds,
                    "progress": access.history,
                    "events": access.events,
                    "buses": access.buses,
                },
                "aircraft": {
                    "first_door_ready_time_seconds": aircraft.first_aircraft_ready_time,
                    "first_entry_time_seconds": aircraft.first_entry_time,
                    "last_seat_time_seconds": aircraft.last_seat_time,
                    "cabin_boarding_seconds": aircraft.cabin_boarding_seconds,
                    "timed_out": aircraft.timed_out,
                    "progress": aircraft.history,
                    "events": aircraft.events,
                    "diagnostics": aircraft.diagnostics,
                },
            },
        },
        replay=replay,
        trajectory=trajectory,
        metrics=metrics,
        diagnostics={
            "preparation_rng_stream": 2,
            "access_rng_stream": 3,
            "aircraft_rng_stream": 4,
            "movement_audit_event_count": len(aircraft.movement_audit),
            "deterministic_serialization": "Python JSON, sorted keys, compact separators, allow_nan=false",
        },
    )


def run_flight_from_manifest(
    scenario_patch: dict[str, Any] | None,
    seed: int | None,
    manifest: list[Passenger],
) -> FlightResult:
    """Run a strategy using an immutable shared passenger manifest."""
    validated_seed = validate_seed(seed)
    scenario = normalize_scenario(scenario_patch)
    calibration, registry = _model_inputs()
    strategy = strategy_by_id(scenario["boarding"]["strategy"])
    passengers = assign_strategy(
        copy.deepcopy(manifest), strategy, RNG(validated_seed).fork(1)
    )
    return _run_assigned_flight(
        scenario, validated_seed, passengers, strategy, calibration, registry
    )


def run_flight(
    scenario_patch: dict[str, Any] | None,
    seed: int | None,
) -> FlightResult:
    validated_seed = validate_seed(seed)
    scenario = normalize_scenario(scenario_patch)
    calibration, registry = _model_inputs()
    strategy = strategy_by_id(scenario["boarding"]["strategy"])
    manifest_rng = RNG(validated_seed).fork(1)
    passengers = generate_manifest(scenario, manifest_rng, calibration)
    assign_strategy(passengers, strategy, manifest_rng)
    return _run_assigned_flight(
        scenario, validated_seed, passengers, strategy, calibration, registry
    )
