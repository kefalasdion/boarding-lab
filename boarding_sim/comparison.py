"""Fair, strategy-neutral comparisons for the public three-lane experience."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from .engine import MODEL_STATUS, MODEL_VERSION, SCHEMA_VERSION, run_flight_from_manifest
from .metrics import summarize_distribution
from .population import generate_manifest
from .prng import RNG
from .serialization import canonical_json_bytes, to_primitive
from .validation import (
    ScenarioValidationError,
    ValidationIssue,
    load_behaviour_calibration,
    normalize_scenario,
    validate_seed,
)

PUBLIC_STRATEGY_IDS = (
    "random_front",
    "back_to_front_zones",
    "strict_steffen",
)

MANIFEST_FIELDS = (
    "id",
    "row",
    "seat",
    "family_id",
    "tolerance_threshold",
    "delay_sensitivity",
    "uncertainty_sensitivity",
    "wait_sensitivity",
    "crowd_sensitivity",
    "social_susceptibility",
    "compliance",
    "information_trust",
    "fatigue",
    "connection_pressure",
    "urgency",
    "walking_speed_mps",
    "bag_count",
    "initial_stress_load",
    "initial_frustration",
)


def manifest_fingerprint(manifest: list[Any]) -> str:
    stable_manifest = [
        {field: getattr(passenger, field) for field in MANIFEST_FIELDS}
        for passenger in sorted(manifest, key=lambda item: item.id)
    ]
    return hashlib.sha256(canonical_json_bytes(stable_manifest)).hexdigest()


def _comparison_scenario(scenario_patch: dict[str, Any] | None) -> dict[str, Any]:
    scenario = normalize_scenario(scenario_patch)
    scenario["preparation"]["policy"] = {
        "mode": "complete_preparation",
        "readinessTarget": 1.0,
        "firstCohortTarget": 1.0,
    }
    return scenario


def run_comparison(
    scenario_patch: dict[str, Any] | None,
    seed: int | None,
) -> dict[str, Any]:
    validated_seed = validate_seed(seed)
    scenario = _comparison_scenario(scenario_patch)
    manifest = generate_manifest(
        scenario, RNG(validated_seed).fork(1), load_behaviour_calibration()
    )
    fingerprint = manifest_fingerprint(manifest)
    results: dict[str, dict[str, Any]] = {}
    for strategy_id in PUBLIC_STRATEGY_IDS:
        strategy_scenario = copy.deepcopy(scenario)
        strategy_scenario["boarding"]["strategy"] = strategy_id
        result = to_primitive(
            run_flight_from_manifest(strategy_scenario, validated_seed, manifest)
        )
        result["manifest_fingerprint"] = fingerprint
        results[strategy_id] = result

    all_valid = all(result["status"] == "valid" for result in results.values())
    ranking = (
        sorted(
            PUBLIC_STRATEGY_IDS,
            key=lambda strategy_id: (
                results[strategy_id]["metrics"]["timings_seconds"][
                    "total_t0_to_last_seat"
                ],
                PUBLIC_STRATEGY_IDS.index(strategy_id),
            ),
        )
        if all_valid
        else []
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "model_version": MODEL_VERSION,
        "seed": validated_seed,
        "status": "valid" if all_valid else "incomplete",
        "model_status": dict(MODEL_STATUS),
        "scenario": scenario,
        "manifest_fingerprint": fingerprint,
        "strategy_order": list(PUBLIC_STRATEGY_IDS),
        "strategies": results,
        "ranking": ranking,
        "winner": ranking[0] if ranking else None,
    }


def _validate_comparison_batch(runs: Any, base_seed: Any) -> tuple[int, int]:
    issues: list[ValidationIssue] = []
    if isinstance(runs, bool) or not isinstance(runs, int) or not (1 <= runs <= 200):
        issues.append(
            ValidationIssue(
                "runs", "invalid_run_count", "Expected an integer from 1 through 200."
            )
        )
    try:
        validated_seed = validate_seed(base_seed, "baseSeed")
    except ScenarioValidationError as error:
        issues.extend(error.issues)
        validated_seed = 0
    if not issues and validated_seed + runs - 1 > 0xFFFFFFFF:
        issues.append(
            ValidationIssue(
                "baseSeed",
                "seed_range_overflow",
                "baseSeed + runs - 1 must not exceed 4294967295.",
            )
        )
    if issues:
        raise ScenarioValidationError(issues)
    return runs, validated_seed


def _compact_strategy_result(result: dict[str, Any]) -> dict[str, Any]:
    timings = result["metrics"]["timings_seconds"]
    experience = result["metrics"]["passenger_experience"]
    return {
        "status": result["status"],
        "preparation_seconds": timings["preparation"],
        "embarkation_seconds": timings["embarkation"],
        "total_seconds": timings["total_t0_to_last_seat"],
        "preparation_frustration_burden": experience[
            "preparation_frustration_burden_f_minutes"
        ]["mean"],
        "embarkation_frustration_burden": experience[
            "embarkation_frustration_burden_f_minutes"
        ]["mean"],
        "total_frustration_burden": experience[
            "total_frustration_burden_f_minutes"
        ]["mean"],
        "correction_events": result["metrics"]["correction_events"],
        "companion_overrides": result["metrics"]["companion_overrides"],
    }


def compact_comparison_record(comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": comparison["seed"],
        "status": comparison["status"],
        "winner": comparison["winner"],
        "manifest_fingerprint": comparison["manifest_fingerprint"],
        "strategies": {
            strategy_id: _compact_strategy_result(result)
            for strategy_id, result in comparison["strategies"].items()
        },
    }


def aggregate_comparison_records(
    records: list[dict[str, Any]], base_seed: int
) -> dict[str, Any]:
    records = sorted(records, key=lambda record: record["seed"])
    summary_keys = (
        "preparation_seconds",
        "embarkation_seconds",
        "total_seconds",
        "preparation_frustration_burden",
        "embarkation_frustration_burden",
        "total_frustration_burden",
        "correction_events",
        "companion_overrides",
    )
    summaries = {
        strategy_id: {
            key: summarize_distribution(
                record["strategies"][strategy_id][key]
                for record in records
                if record["strategies"][strategy_id]["status"] == "valid"
            )
            for key in summary_keys
        }
        for strategy_id in PUBLIC_STRATEGY_IDS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "model_version": MODEL_VERSION,
        "base_seed": base_seed,
        "requested_runs": len(records),
        "valid_comparisons": sum(record["status"] == "valid" for record in records),
        "win_counts": {
            strategy_id: sum(record["winner"] == strategy_id for record in records)
            for strategy_id in PUBLIC_STRATEGY_IDS
        },
        "strategy_run_counts": {
            strategy_id: {
                "valid": sum(
                    record["strategies"][strategy_id]["status"] == "valid"
                    for record in records
                ),
                "timed_out": sum(
                    record["strategies"][strategy_id]["status"] == "timed_out"
                    for record in records
                ),
                "invalid": sum(
                    record["strategies"][strategy_id]["status"] == "invalid"
                    for record in records
                ),
            }
            for strategy_id in PUBLIC_STRATEGY_IDS
        },
        "summaries": summaries,
        "run_records": records,
    }


def run_comparison_monte_carlo(
    scenario_patch: dict[str, Any] | None,
    runs: int,
    base_seed: int,
) -> dict[str, Any]:
    validated_runs, validated_seed = _validate_comparison_batch(runs, base_seed)
    records: list[dict[str, Any]] = []
    for offset in range(validated_runs):
        comparison = run_comparison(scenario_patch, validated_seed + offset)
        records.append(compact_comparison_record(comparison))
    return aggregate_comparison_records(records, validated_seed)
