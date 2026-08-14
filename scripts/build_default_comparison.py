"""Generate the tracked representative replay and 100-run fair summary."""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from boarding_sim.comparison import (
    PUBLIC_STRATEGY_IDS,
    aggregate_comparison_records,
    compact_public_comparison,
    compact_comparison_record,
    run_comparison,
)
from boarding_sim.engine import MODEL_VERSION, SCHEMA_VERSION
from boarding_sim.serialization import canonical_json_bytes, to_primitive

DEFAULT_ARTIFACT_PATH = PROJECT_ROOT / "web" / "data" / "default-comparison.json"
BASE_SEED = 20260813
DEFAULT_RUNS = 100
DEFAULT_SCENARIO_PATCH = {"preparation": {"replaySampleSeconds": 6}}


def _compact_seed(seed: int) -> dict[str, Any]:
    return compact_comparison_record(run_comparison(DEFAULT_SCENARIO_PATCH, seed))


def build_records_parallel(
    runs: int = DEFAULT_RUNS,
    base_seed: int = BASE_SEED,
    workers: int | None = None,
) -> list[dict[str, Any]]:
    worker_count = workers or min(4, os.cpu_count() or 1)
    records: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(_compact_seed, base_seed + offset): offset
            for offset in range(runs)
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            records.append(future.result())
            if completed % 10 == 0 or completed == runs:
                print(f"Completed {completed}/{runs} fair comparisons", flush=True)
    return sorted(records, key=lambda record: record["seed"])


def representative_seed(summary: dict[str, Any]) -> int:
    valid_records = [
        record for record in summary["run_records"] if record["status"] == "valid"
    ]
    if not valid_records:
        return summary["base_seed"]
    medians = {
        strategy_id: summary["summaries"][strategy_id]["total_seconds"].p50
        if hasattr(summary["summaries"][strategy_id]["total_seconds"], "p50")
        else summary["summaries"][strategy_id]["total_seconds"]["p50"]
        for strategy_id in PUBLIC_STRATEGY_IDS
    }

    def distance(record: dict[str, Any]) -> tuple[float, int]:
        score = 0.0
        for strategy_id in PUBLIC_STRATEGY_IDS:
            median = medians[strategy_id]
            total = record["strategies"][strategy_id]["total_seconds"]
            score += ((total - median) / max(median, 1.0)) ** 2
        return score, record["seed"]

    return min(valid_records, key=distance)["seed"]


def assemble_default_artifact(records: list[dict[str, Any]]) -> dict[str, Any]:
    full_summary = aggregate_comparison_records(records, BASE_SEED)
    selected_seed = representative_seed(full_summary)
    summary = dict(full_summary)
    summary.pop("run_records", None)
    representative = compact_public_comparison(
        run_comparison(DEFAULT_SCENARIO_PATCH, selected_seed)
    )
    return to_primitive(
        {
            "schema_version": SCHEMA_VERSION,
            "model_version": MODEL_VERSION,
            "base_seed": BASE_SEED,
            "scenario_patch": DEFAULT_SCENARIO_PATCH,
            "representative_seed": selected_seed,
            "representative": representative,
            "summary": summary,
        }
    )


def build_default_artifact(
    runs: int = DEFAULT_RUNS,
    workers: int | None = None,
) -> bytes:
    records = build_records_parallel(runs, BASE_SEED, workers)
    return canonical_json_bytes(assemble_default_artifact(records))


def load_default_artifact() -> dict[str, Any]:
    with DEFAULT_ARTIFACT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument(
        "--reuse-records",
        action="store_true",
        help="Reuse records from an existing artifact while rebuilding its representative payload.",
    )
    parser.add_argument(
        "--recompact-existing",
        action="store_true",
        help="Recompact an existing representative without rerunning simulations.",
    )
    arguments = parser.parse_args()
    if arguments.runs != DEFAULT_RUNS:
        raise SystemExit("The tracked default artifact must contain exactly 100 runs.")
    if arguments.recompact_existing:
        artifact = load_default_artifact()
        artifact["representative"] = compact_public_comparison(
            artifact["representative"]
        )
        payload = canonical_json_bytes(artifact)
    elif arguments.reuse_records:
        records = load_default_artifact()["summary"]["run_records"]
        payload = canonical_json_bytes(assemble_default_artifact(records))
    else:
        payload = build_default_artifact(arguments.runs, arguments.workers)
    DEFAULT_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ARTIFACT_PATH.write_bytes(payload)
    print(f"Wrote {len(payload):,} bytes to {DEFAULT_ARTIFACT_PATH}")


if __name__ == "__main__":
    main()
