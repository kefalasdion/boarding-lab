"""Bake one playable replay per gate-agent call rate for the public explorer.

The published web page must not reproduce any part of the model, so this script
resolves every passenger to a screen-independent lane coordinate here, in Python,
and emits quantised integer tracks. The browser only interpolates and draws.

Lane space is the unit square: `u` runs left (gate) to right (seated), `v` runs
top to bottom within one strategy's lane. The proportions match the existing
race canvas so the explorer, the local app and the rendered video agree.

    python3 -m scripts.build_call_rate_explorer --workers 6
"""

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

from boarding_sim.comparison import PUBLIC_STRATEGY_IDS, run_comparison
from boarding_sim.engine import MODEL_VERSION

SCHEMA = "boarding-explorer/1"
SEED = 20260888
FRAME_SECONDS = 3.0

# Every rate the slider can select, in seconds per passenger call.
CALL_RATES = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0)

STRATEGY_LABELS = {
    "random_front": ("Random", "One announcement, one loose queue"),
    "back_to_front_zones": ("Back-to-front", "Six five-row zones, rear first"),
    "strict_steffen": ("Strict Steffen", "Every passenger called individually"),
}

# Lane proportions, copied from web/js/race-canvas.js so all three surfaces agree.
GATE_U0, GATE_USPAN = 0.13, 0.29
GATE_V0, GATE_VSPAN = 0.13, 0.74
DOOR_U = 0.635
AISLE_U0, AISLE_USPAN = 0.66, 0.30
SEAT_U0, SEAT_USPAN = 0.675, 0.285
SEAT_OFFSETS = (-0.26, -0.17, -0.09, 0.09, 0.17, 0.26)
AISLE_CELLS = 60.0


def _frame_pair(frames: list[list[Any]], time: float) -> tuple[Any, Any, float]:
    """Match the browser's binary search so baked motion matches the live app."""
    if not frames:
        return None, None, 0.0
    low, high = 0, len(frames) - 1
    while low < high:
        middle = -(-(low + high) // 2)
        if frames[middle][0] <= time:
            low = middle
        else:
            high = middle - 1
    first = frames[low]
    second = frames[min(low + 1, len(frames) - 1)]
    span = second[0] - first[0]
    amount = min(1.0, max(0.0, (time - first[0]) / span)) if span > 0 else 0.0
    return first, second, amount


def _mix(first: float, second: float, amount: float) -> float:
    return first + (second - first) * amount


def _state(frame: Any, passenger_id: int) -> Any:
    if not frame:
        return None
    states = frame[3]
    if passenger_id < len(states) and states[passenger_id][0] == passenger_id:
        return states[passenger_id]
    for state in states:
        if state[0] == passenger_id:
            return state
    return None


class LaneBaker:
    """Resolve one strategy's passengers to lane coordinates at any clock time."""

    def __init__(self, result: dict[str, Any]) -> None:
        self.trajectory = result["trajectory"]
        replay = result["replay"]
        self.replay = replay
        self.gate_frames = replay["gate"]["frames"]
        self.frustration_frames = replay["frustration_frames"]
        self.layout = replay["gate"]["layout"]
        self.tracks = replay["passenger_tracks"]
        self.preparation_end = result["metrics"]["timings_seconds"]["preparation"]
        self.ends_at = replay["ends_at_seconds"]
        codes = replay["event_codebook"]
        self.entry_code = codes["aircraft_entered"]
        self.move_code = codes["aisle_moved"]
        self.seated_code = codes["seated"]
        self.events: dict[int, list[list[Any]]] = {}
        for event in replay["aircraft_events"]:
            self.events.setdefault(event[2], []).append(event)
        self.slots = {slot[0]: slot for slot in replay["gate"]["slots"]}

    def gate_point(self, passenger_id: int, time: float) -> tuple[float, float]:
        first, second, amount = _frame_pair(self.gate_frames, time)
        first_state = _state(first, passenger_id)
        second_state = _state(second, passenger_id) or first_state
        x = _mix(
            first_state[1] if first_state else 0.0,
            second_state[1] if second_state else 0.0,
            amount,
        )
        y = _mix(
            first_state[2] if first_state else 0.0,
            second_state[2] if second_state else 0.0,
            amount,
        )
        return (
            GATE_U0 + (x / self.layout["width_m"]) * GATE_USPAN,
            GATE_V0 + (y / self.layout["height_m"]) * GATE_VSPAN,
        )

    def point(self, passenger_id: int, time: float) -> tuple[float, float]:
        if time <= self.preparation_end:
            return self.gate_point(passenger_id, time)

        start = self.gate_point(passenger_id, self.preparation_end)
        events = self.events.get(passenger_id, [])
        entered = next((e for e in events if e[1] == self.entry_code), None)
        seated = next((e for e in events if e[1] == self.seated_code), None)

        if not entered or time < entered[0]:
            end_time = entered[0] if entered else self.ends_at
            span = max(1.0, end_time - self.preparation_end)
            progress = min(1.0, max(0.0, (time - self.preparation_end) / span))
            return _mix(start[0], DOOR_U, progress), _mix(start[1], 0.5, progress)

        track = self.tracks[str(passenger_id)]
        if seated and time >= seated[0]:
            column = "ABCDEF".find(track[1])
            offset = SEAT_OFFSETS[column] if 0 <= column < 6 else 0.0
            return SEAT_U0 + (track[0] - 1) / 29.0 * SEAT_USPAN, 0.5 + offset

        aisle_cell = 0.0
        has_movement = False
        for event in events:
            if event[0] > time:
                break
            if event[1] == self.move_code:
                aisle_cell = event[5]
                has_movement = True
        if not has_movement and seated:
            span = max(1.0, seated[0] - entered[0])
            progress = min(1.0, max(0.0, (time - entered[0]) / span))
            aisle_cell = progress * max(0.0, (track[0] - 1) * 2)
        return AISLE_U0 + min(1.0, aisle_cell / AISLE_CELLS) * AISLE_USPAN, 0.5

    def counts(self, time: float) -> tuple[int, int]:
        """Passengers correctly staged, and passengers seated, at this instant.

        Both are model outputs sampled on the trajectory, held rather than
        interpolated: a count that reads 143.6 is not a count.
        """
        prepared = 0
        seated = 0
        for sample in self.trajectory:
            if sample["time_seconds"] > time:
                break
            prepared = sample["prepared_count"]
            seated = sample["seated_count"]
        return prepared, seated

    def frustration(self, passenger_id: int, time: float) -> float:
        gate_phase = time <= self.preparation_end
        frames = self.gate_frames if gate_phase else self.frustration_frames
        index = 3 if gate_phase else 1
        first, second, amount = _frame_pair(frames, time)
        first_state = _state(first, passenger_id)
        second_state = _state(second, passenger_id) or first_state
        return _mix(
            first_state[index] if first_state else 0.0,
            second_state[index] if second_state else 0.0,
            amount,
        )


def _delta(values: list[int]) -> list[int]:
    out = [values[0]] if values else []
    for index in range(1, len(values)):
        out.append(values[index] - values[index - 1])
    return out


def _quantise(value: float) -> int:
    return max(0, min(255, round(value * 255.0)))


def _bake_strategy(result: dict[str, Any], times: list[float]) -> dict[str, Any]:
    baker = LaneBaker(result)
    ids = sorted(int(key) for key in baker.tracks)
    us: list[int] = []
    vs: list[int] = []
    fs: list[int] = []
    for passenger_id in ids:
        track_u: list[int] = []
        track_v: list[int] = []
        track_f: list[int] = []
        for time in times:
            u, v = baker.point(passenger_id, time)
            track_u.append(_quantise(u))
            track_v.append(_quantise(v))
            track_f.append(_quantise(baker.frustration(passenger_id, time)))
        us.extend(_delta(track_u))
        vs.extend(_delta(track_v))
        fs.extend(_delta(track_f))

    prepared: list[int] = []
    seated: list[int] = []
    for time in times:
        staged, sat = baker.counts(time)
        prepared.append(staged)
        seated.append(sat)

    metrics = result["metrics"]
    timings = metrics["timings_seconds"]
    experience = metrics["passenger_experience"]
    label, subtitle = STRATEGY_LABELS[result["strategy"]["id"]]
    return {
        "id": result["strategy"]["id"],
        "label": label,
        "subtitle": subtitle,
        "timings": {
            "preparation": round(timings["preparation"], 1),
            "boardingStarted": round(
                timings["total_t0_to_last_seat"] - timings["cabin_boarding"], 1
            ),
            "cabinBoarding": round(timings["cabin_boarding"], 1),
            "total": round(timings["total_t0_to_last_seat"], 1),
        },
        "burden": {
            "preparation": round(
                experience["preparation_frustration_burden_f_minutes"]["mean"], 3
            ),
            "embarkation": round(
                experience["embarkation_frustration_burden_f_minutes"]["mean"], 3
            ),
            "total": round(experience["frustration_burden_f_minutes"]["mean"], 3),
        },
        "separations": metrics["companion_separations"],
        "corrections": metrics["correction_events"],
        "u": us,
        "v": vs,
        "f": fs,
        "prepared": _delta(prepared),
        "seated": _delta(seated),
    }


def build_call_rate(rate: float) -> dict[str, Any]:
    patch = {
        "preparation": {
            "replaySampleSeconds": 2,
            "release": {"passengerIntervalSeconds": rate},
        }
    }
    comparison = run_comparison(patch, SEED)
    if comparison["status"] != "valid":
        raise RuntimeError(f"call rate {rate}s produced an incomplete comparison")

    longest = max(
        comparison["strategies"][sid]["metrics"]["timings_seconds"][
            "total_t0_to_last_seat"
        ]
        for sid in PUBLIC_STRATEGY_IDS
    )
    frame_count = int(longest // FRAME_SECONDS) + 2
    times = [index * FRAME_SECONDS for index in range(frame_count)]

    return {
        "callRateSeconds": rate,
        "frames": frame_count,
        "durationSeconds": round(longest, 1),
        "winner": comparison["winner"],
        "strategies": [
            _bake_strategy(comparison["strategies"][sid], times)
            for sid in PUBLIC_STRATEGY_IDS
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 1))
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "output" / "explorer",
        help="directory to write one JSON file per call rate, plus an index",
    )
    arguments = parser.parse_args()
    arguments.out.mkdir(parents=True, exist_ok=True)

    results: dict[float, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures = {executor.submit(build_call_rate, rate): rate for rate in CALL_RATES}
        for done, future in enumerate(as_completed(futures), start=1):
            rate = futures[future]
            results[rate] = future.result()
            print(f"baked {done}/{len(CALL_RATES)} · {rate}s per passenger", flush=True)

    index = {
        "schema": SCHEMA,
        "modelVersion": MODEL_VERSION,
        "seed": SEED,
        "frameSeconds": FRAME_SECONDS,
        "passengerCount": 180,
        "callRates": [
            {
                "seconds": rate,
                "file": f"call-{str(rate).replace('.', '-')}.json",
                "winner": results[rate]["winner"],
                "totals": {
                    strategy["id"]: strategy["timings"]["total"]
                    for strategy in results[rate]["strategies"]
                },
            }
            for rate in CALL_RATES
        ],
    }
    (arguments.out / "index.json").write_text(
        json.dumps(index, separators=(",", ":")), encoding="utf-8"
    )
    for rate in CALL_RATES:
        name = f"call-{str(rate).replace('.', '-')}.json"
        payload = dict(results[rate])
        payload["schema"] = SCHEMA
        payload["frameSeconds"] = FRAME_SECONDS
        (arguments.out / name).write_text(
            json.dumps(payload, separators=(",", ":")), encoding="utf-8"
        )

    total = sum(path.stat().st_size for path in arguments.out.glob("*.json"))
    print(f"wrote {len(CALL_RATES) + 1} files, {total / 1024 / 1024:.2f} MB raw")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
