"""Scenario loading, strict merging, and domain validation."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO_PATH = PROJECT_ROOT / "config" / "default-scenario.json"
CALIBRATION_PATH = PROJECT_ROOT / "config" / "behaviour-calibration.json"

STRATEGY_IDS = {
    "random_front",
    "split_half_two_door",
    "wilma",
    "back_to_front_zones",
    "wilma_zones",
    "steffen_companion",
    "split_wilma_two_door",
}
SERVICE_MODELS = {"field_calibrated", "user_occupancy_rule"}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


class ScenarioValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = sorted(issues, key=lambda item: (item.path, item.code, item.message))
        super().__init__("; ".join(f"{item.path}: {item.message}" for item in self.issues))


def _load_json(path: Path) -> dict[str, Any] | list[Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_default_scenario() -> dict[str, Any]:
    return copy.deepcopy(_load_json(DEFAULT_SCENARIO_PATH))


def load_behaviour_calibration() -> dict[str, Any]:
    return copy.deepcopy(_load_json(CALIBRATION_PATH))


def _strict_merge(base: dict[str, Any], patch: dict[str, Any], prefix: str, issues: list[ValidationIssue]) -> None:
    for key, value in patch.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in base:
            issues.append(ValidationIssue(path, "unknown_parameter", "Parameter is not defined by the scenario schema."))
            continue
        current = base[key]
        if isinstance(current, dict):
            if not isinstance(value, dict):
                issues.append(ValidationIssue(path, "invalid_type", "Expected an object."))
            else:
                _strict_merge(current, value, path, issues)
        else:
            base[key] = copy.deepcopy(value)


def _number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _range(issues: list[ValidationIssue], scenario: dict[str, Any], path: str, minimum: float, maximum: float | None = None, *, inclusive_min: bool = True) -> None:
    value: Any = scenario
    for part in path.split("."):
        value = value[part]
    valid = _number(value) and (value >= minimum if inclusive_min else value > minimum)
    if maximum is not None:
        valid = valid and value <= maximum
    if not valid:
        bound = f"between {minimum} and {maximum}" if maximum is not None else f"greater than {'or equal to ' if inclusive_min else ''}{minimum}"
        issues.append(ValidationIssue(path, "out_of_range", f"Expected a finite number {bound}."))


def _validate(scenario: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if scenario["aircraft"]["type"] != "A320_180" or scenario["aircraft"]["rows"] != 30 or scenario["aircraft"]["seatsPerRow"] != 6:
        issues.append(ValidationIssue("aircraft", "unsupported_geometry", "Only the A320_180 30-row, six-seat geometry is implemented."))
    _range(issues, scenario, "aircraft.loadFactor", 0.01, 1.0)
    for path in ("flightContext.delayMinutes", "flightContext.priorDelayUpdates", "flightContext.priorGateWaitMinutes", "flightContext.priorAirportDwellMinutes"):
        _range(issues, scenario, path, 0)
    _range(issues, scenario, "flightContext.connectionPressureShare", 0, 1)
    for path in ("population.familyPassengerShare", "population.handLuggageShare", "population.twoBagShareAmongBagPassengers"):
        _range(issues, scenario, path, 0, 1)
    if scenario["preparation"]["policy"]["mode"] != "strict_preparation":
        issues.append(ValidationIssue("preparation.policy.mode", "unsupported_policy", "Only strict_preparation is implemented in schema version 1."))
    for path in ("preparation.policy.readinessTarget", "preparation.policy.firstCohortTarget"):
        _range(issues, scenario, path, 0.01, 1.0)
    for path in ("preparation.gateUsableAreaM2", "preparation.averageStartDistanceM", "preparation.maxPreparationSeconds"):
        _range(issues, scenario, path, 0, inclusive_min=False)
    if not isinstance(scenario["access"]["mode"], str) or scenario["access"]["mode"] not in {"bridge", "bus"}:
        issues.append(ValidationIssue("access.mode", "invalid_choice", "Expected bridge or bus."))
    for path in ("access.bridgeLengthM", "access.bridgeWalkSpeedMps", "access.gateScanMeanSeconds", "access.bridgeMinimumHeadwaySeconds", "access.busCount", "access.busCapacity", "access.busBoardMeanSeconds", "access.busTravelMeanSeconds", "access.busUnloadMeanSeconds"):
        _range(issues, scenario, path, 0, inclusive_min=False)
    _range(issues, scenario, "access.busTravelSdSeconds", 0)
    geometry_values = (
        scenario["aircraft"]["rows"],
        scenario["aircraft"]["seatsPerRow"],
        scenario["aircraft"]["loadFactor"],
    )
    passenger_count = round(math.prod(geometry_values)) if all(_number(value) for value in geometry_values) else None
    bus_values = (scenario["access"]["busCount"], scenario["access"]["busCapacity"])
    if scenario["access"]["mode"] == "bus" and passenger_count is not None and all(_number(value) for value in bus_values) and math.prod(bus_values) < passenger_count:
        issues.append(ValidationIssue("access.busCapacity", "insufficient_capacity", "The configured single-trip bus fleet cannot carry all passengers."))
    if not isinstance(scenario["boarding"]["strategy"], str) or scenario["boarding"]["strategy"] not in STRATEGY_IDS:
        issues.append(ValidationIssue("boarding.strategy", "invalid_choice", "Unknown boarding strategy."))
    if isinstance(scenario["boarding"]["strategy"], str) and scenario["boarding"]["strategy"] in {"split_half_two_door", "split_wilma_two_door"} and scenario["access"]["mode"] != "bus":
        issues.append(ValidationIssue("access.mode", "incompatible_access", "Two-door strategies require bus access with independent front and rear unloading streams."))
    if not isinstance(scenario["boarding"]["serviceModel"], str) or scenario["boarding"]["serviceModel"] not in SERVICE_MODELS:
        issues.append(ValidationIssue("boarding.serviceModel", "invalid_choice", "Unknown row-service model."))
    if scenario["boarding"]["cellSizeM"] != 0.4:
        issues.append(ValidationIssue("boarding.cellSizeM", "fixed_reference_value", "The reference aircraft CA requires 0.4 m cells."))
    if scenario["boarding"]["aisleCellsPerRow"] != 2:
        issues.append(ValidationIssue("boarding.aisleCellsPerRow", "unsupported_geometry", "The reference A320 geometry uses two aisle cells per row."))
    for path in ("boarding.dtSeconds", "boarding.walkingSpeedMps", "boarding.baggageWeibullShape", "boarding.baggageWeibullScaleSeconds", "boarding.customSeatBaseSeconds", "boarding.customIncrementSeconds", "boarding.customIncrementLoadStep", "boarding.maxBoardingSeconds"):
        _range(issues, scenario, path, 0, inclusive_min=False)
    _range(issues, scenario, "boarding.customLoadThreshold", 0, 1)
    triangular = scenario["boarding"]["seatMovementTriangularSeconds"]
    if not isinstance(triangular, list) or len(triangular) != 3 or not all(_number(x) for x in triangular) or not (0 < triangular[0] <= triangular[1] <= triangular[2]):
        issues.append(ValidationIssue("boarding.seatMovementTriangularSeconds", "invalid_distribution", "Expected positive [minimum, mode, maximum] values."))
    _range(issues, scenario, "metrics.frustrationThreshold", 0, 1)
    _range(issues, scenario, "metrics.historySampleSeconds", 1, inclusive_min=True)
    return issues


def normalize_scenario(patch: dict[str, Any] | None = None) -> dict[str, Any]:
    scenario = load_default_scenario()
    issues: list[ValidationIssue] = []
    if patch is not None:
        if not isinstance(patch, dict):
            raise ScenarioValidationError([ValidationIssue("scenario", "invalid_type", "Expected an object.")])
        _strict_merge(scenario, patch, "", issues)
    if not issues:
        issues.extend(_validate(scenario))
    if issues:
        raise ScenarioValidationError(issues)
    return scenario


def validate_seed(seed: Any, path: str = "seed") -> int:
    if isinstance(seed, bool) or not isinstance(seed, int) or not (0 <= seed <= 0xFFFFFFFF):
        raise ScenarioValidationError([ValidationIssue(path, "invalid_seed", "Expected an integer from 0 through 4294967295.")])
    return seed
