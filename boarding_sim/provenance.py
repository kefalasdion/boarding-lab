"""Parameter provenance registry and coverage validation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "config" / "parameter-registry.json"
DISPLAY_CATEGORIES = {"calibrated", "literature", "user", "operational", "provisional"}


def load_parameter_registry() -> list[dict[str, Any]]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return copy.deepcopy(json.load(handle))


def _leaf_paths(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else key
            paths.extend(_leaf_paths(value[key], child))
        return paths
    return [prefix]


def _leaf_values(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else key
            flattened.update(_leaf_values(value[key], child))
        return flattened
    return {prefix: value}


def validate_registry_coverage(scenario: dict[str, Any], calibration: dict[str, Any], registry: list[dict[str, Any]]) -> list[str]:
    configured_values = {
        **_leaf_values(scenario),
        **_leaf_values(calibration, "behaviour"),
    }
    expected = set(configured_values)
    issues: list[str] = []
    paths: list[str] = []
    for index, entry in enumerate(registry):
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            issues.append(f"registry[{index}]: missing path")
            continue
        paths.append(path)
        for key in ("value", "status", "source", "note", "category"):
            if key not in entry:
                issues.append(f"{path}: missing {key}")
        if entry.get("category") not in DISPLAY_CATEGORIES:
            issues.append(f"{path}: unsupported category {entry.get('category')!r}")
        if path in configured_values and entry.get("value") != configured_values[path]:
            issues.append(f"{path}: registry value does not match configuration")
    duplicates = sorted({path for path in paths if paths.count(path) > 1})
    issues.extend(f"{path}: duplicate registry entry" for path in duplicates)
    registered = set(paths)
    issues.extend(f"{path}: missing provenance" for path in sorted(expected - registered))
    issues.extend(f"{path}: registry path has no configurable value" for path in sorted(registered - expected))
    return sorted(issues)
