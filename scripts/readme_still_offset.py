"""Video offset, in seconds, of the frame the README uses as its still.

The recorder compresses the whole race into a fixed wall-clock length, so the
video second that shows a given simulated moment depends on how long the run
took. This resolves the moment Strict Steffen's queue is complete.
"""

from __future__ import annotations

import json
from pathlib import Path

RACE_SECONDS = 34.0  # must match record_linkedin_video.mjs
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    artifact = json.loads(
        (PROJECT_ROOT / "web" / "data" / "default-comparison.json").read_text()
    )
    representative = artifact["representative"]
    strategies = representative["strategies"]
    longest = max(
        strategies[strategy_id]["replay"]["ends_at_seconds"]
        for strategy_id in representative["strategy_order"]
    )
    ready = strategies["strict_steffen"]["metrics"]["timings_seconds"]["preparation"]
    speed = longest / RACE_SECONDS
    print(f"{ready / speed:.2f}")


if __name__ == "__main__":
    main()
