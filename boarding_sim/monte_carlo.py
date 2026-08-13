"""Deterministic Monte Carlo flight batches and uncertainty summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .engine import MODEL_VERSION, SCHEMA_VERSION, run_flight
from .metrics import summarize_distribution
from .serialization import to_primitive
from .validation import (
    ScenarioValidationError,
    ValidationIssue,
    normalize_scenario,
    validate_seed,
)


@dataclass
class MonteCarloRunRecord:
    seed: int
    status: str
    metrics: dict[str, Any] | None = None
    error_code: str | None = None


@dataclass
class MonteCarloResult:
    schema_version: str
    model_version: str
    base_seed: int
    requested_runs: int
    valid_runs: int
    timed_out_runs: int
    invalid_runs: int
    summaries: dict[str, Any]
    run_records: list[MonteCarloRunRecord]
    scenario: dict[str, Any] | None = None


SUMMARY_KEYS = (
    "preparation_seconds",
    "access_seconds",
    "embarkation_seconds",
    "cabin_boarding_seconds",
    "total_seconds",
    "mean_frustration_burden",
    "p90_frustration_burden",
    "mean_peak_frustration",
    "p90_peak_frustration",
    "share_peak_above_threshold",
    "correction_events",
)


def _extract_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    primitive = to_primitive(metrics)
    timings = primitive["timings_seconds"]
    experience = primitive["passenger_experience"]
    return {
        "preparation_seconds": timings["preparation"],
        "access_seconds": timings["access_until_last_door_arrival"],
        "embarkation_seconds": timings["embarkation"],
        "cabin_boarding_seconds": timings["cabin_boarding"],
        "total_seconds": timings["total_t0_to_last_seat"],
        "mean_frustration_burden": experience["frustration_burden_f_minutes"]["mean"],
        "p90_frustration_burden": experience["frustration_burden_f_minutes"]["p90"],
        "mean_peak_frustration": experience["peak_frustration"]["mean"],
        "p90_peak_frustration": experience["peak_frustration"]["p90"],
        "share_peak_above_threshold": experience["share_peak_above_threshold"],
        "correction_events": primitive["correction_events"],
    }


def aggregate_run_records(
    records: list[MonteCarloRunRecord],
    base_seed: int,
    scenario: dict[str, Any] | None = None,
) -> MonteCarloResult:
    valid_records = [record for record in records if record.status == "valid" and record.metrics is not None]
    extracted = [_extract_metrics(record.metrics) for record in valid_records]
    summaries = {
        key: summarize_distribution(item[key] for item in extracted) if extracted else None
        for key in SUMMARY_KEYS
    }
    return MonteCarloResult(
        schema_version=SCHEMA_VERSION,
        model_version=MODEL_VERSION,
        base_seed=base_seed,
        requested_runs=len(records),
        valid_runs=len(valid_records),
        timed_out_runs=sum(record.status == "timed_out" for record in records),
        invalid_runs=sum(record.status == "invalid" for record in records),
        summaries=summaries,
        run_records=records,
        scenario=scenario,
    )


def _validate_batch(runs: Any, base_seed: Any) -> tuple[int, int]:
    issues: list[ValidationIssue] = []
    if isinstance(runs, bool) or not isinstance(runs, int) or not (1 <= runs <= 10000):
        issues.append(
            ValidationIssue(
                "runs", "invalid_run_count", "Expected an integer from 1 through 10000."
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


def run_monte_carlo(
    scenario_patch: dict[str, Any] | None,
    runs: int,
    base_seed: int,
) -> MonteCarloResult:
    validated_runs, validated_base_seed = _validate_batch(runs, base_seed)
    scenario = normalize_scenario(scenario_patch)
    records: list[MonteCarloRunRecord] = []
    for run_index in range(validated_runs):
        seed = validated_base_seed + run_index
        try:
            result = run_flight(scenario, seed)
            records.append(
                MonteCarloRunRecord(
                    seed=seed,
                    status=result.status,
                    metrics=result.metrics,
                )
            )
        except Exception as error:
            records.append(
                MonteCarloRunRecord(
                    seed=seed,
                    status="invalid",
                    error_code=type(error).__name__,
                )
            )
    return aggregate_run_records(records, validated_base_seed, scenario)
