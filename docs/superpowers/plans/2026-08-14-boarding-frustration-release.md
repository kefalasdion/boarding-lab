# Boarding Frustration Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the preparation model with a gate-agent call bottleneck, then produce a LinkedIn video, a research collection and an open-source-ready repository from the corrected results.

**Architecture:** A new pure `boarding_sim/release.py` computes each passenger's eligibility time from the strategy and their rank; `simulate_preparation` gates movement on it and emits call events. The browser gains a per-lane live frustration figure and a query-parameter capture layout. A Playwright script records that layout and ffmpeg converts it. Documentation and repository packaging follow.

**Tech Stack:** Python 3.11 standard library only, Node 20 with `node --test`, Playwright, ffmpeg, vanilla ES modules and CSS.

**Spec:** `docs/superpowers/specs/2026-08-14-boarding-frustration-release-design.md`

## Global Constraints

- Python remains the single simulation authority; browser code renders serialized results and may not reproduce strategy rules, frustration formulas or readiness policy.
- Every run requires an explicit 32-bit integer seed; identical scenario and seed must produce byte-equivalent results.
- Release times must consume no random numbers.
- `zoneIntervalSeconds` is `20.0`; `passengerIntervalSeconds` is `4.0`. Both are provisional.
- `maxPreparationSeconds` stays `1800`. Never raise it to force a completed race.
- Preparation and frustration outputs are described as **model-predicted** and provisional. Aircraft mechanics may be described as literature-backed.
- Every configurable leaf value needs a `config/parameter-registry.json` entry, keyed `behaviour.<path>` for calibration leaves.
- Never create a GitHub repository, add a remote, or push.
- Python suite: `python3 -m unittest discover -s tests -p 'test_*.py'`. Node suite: `npm test`. Both stay green after every task.

---

### Task 1: Release schedule

**Files:**
- Create: `boarding_sim/release.py`
- Modify: `boarding_sim/strategies.py` (add `release_mode` field and `strategy_release_mode`)
- Modify: `config/behaviour-calibration.json` (add `preparationRelease`)
- Modify: `config/parameter-registry.json` (add two `behaviour.preparationRelease.*` entries)
- Test: `tests/test_release.py`

**Interfaces:**
- Consumes: `Passenger` (`id`, `prep_cohort`, `boarding_rank`), `Strategy`, `SimulationEvent` from `boarding_sim.models`; `apply_companion_policy` has already set `prep_cohort` and `boarding_rank` before these functions are called.
- Produces:
  - `strategy_release_mode(strategy: Strategy) -> str` returning `"general" | "cohort" | "individual"`
  - `release_schedule(passengers: list[Passenger], strategy: Strategy, calibration: dict[str, Any]) -> dict[int, float]` mapping passenger id to eligibility time in seconds
  - `release_events(passengers: list[Passenger], strategy: Strategy, schedule: dict[int, float]) -> list[SimulationEvent]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_release.py`:

```python
import unittest

from boarding_sim.population import generate_population
from boarding_sim.prng import RNG
from boarding_sim.release import (
    release_events,
    release_schedule,
    strategy_release_mode,
)
from boarding_sim.strategies import strategy_by_id
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario


def _population(strategy_id):
    scenario = normalize_scenario()
    calibration = load_behaviour_calibration()
    strategy = strategy_by_id(strategy_id)
    passengers = generate_population(scenario, strategy, RNG(4242), calibration)
    return passengers, strategy, calibration


class ReleaseModeTests(unittest.TestCase):
    def test_single_cohort_strategies_use_one_general_call(self):
        self.assertEqual(strategy_release_mode(strategy_by_id("random_front")), "general")

    def test_multi_cohort_strategies_default_to_zone_calls(self):
        self.assertEqual(
            strategy_release_mode(strategy_by_id("back_to_front_zones")), "cohort"
        )
        self.assertEqual(strategy_release_mode(strategy_by_id("wilma")), "cohort")

    def test_strict_steffen_is_called_passenger_by_passenger(self):
        self.assertEqual(
            strategy_release_mode(strategy_by_id("strict_steffen")), "individual"
        )


class ReleaseScheduleTests(unittest.TestCase):
    def test_random_releases_every_passenger_at_zero(self):
        passengers, strategy, calibration = _population("random_front")
        schedule = release_schedule(passengers, strategy, calibration)
        self.assertEqual(set(schedule.values()), {0.0})
        self.assertEqual(len(schedule), len(passengers))

    def test_back_to_front_releases_zones_twenty_seconds_apart_rear_first(self):
        passengers, strategy, calibration = _population("back_to_front_zones")
        schedule = release_schedule(passengers, strategy, calibration)
        by_cohort = {}
        for passenger in passengers:
            by_cohort.setdefault(passenger.prep_cohort, set()).add(schedule[passenger.id])
        for cohort, times in by_cohort.items():
            self.assertEqual(len(times), 1, f"cohort {cohort} must share one release time")
        ordered = [by_cohort[cohort].pop() for cohort in sorted(by_cohort)]
        self.assertEqual(ordered, [0.0, 20.0, 40.0, 60.0, 80.0, 100.0])
        rear_rows = {p.row for p in passengers if schedule[p.id] == 0.0}
        self.assertTrue(min(rear_rows) >= 26, "cohort released first must be the rear zone")

    def test_strict_steffen_releases_one_passenger_every_four_seconds(self):
        passengers, strategy, calibration = _population("strict_steffen")
        schedule = release_schedule(passengers, strategy, calibration)
        times = sorted(schedule.values())
        self.assertEqual(len(set(times)), len(passengers))
        self.assertEqual(times[0], 0.0)
        self.assertEqual(times[-1], 716.0)
        self.assertEqual(times, [index * 4.0 for index in range(len(passengers))])

    def test_release_times_follow_exact_boarding_order(self):
        passengers, strategy, calibration = _population("strict_steffen")
        schedule = release_schedule(passengers, strategy, calibration)
        for passenger in passengers:
            self.assertEqual(schedule[passenger.id], passenger.boarding_rank * 4.0)


class ReleaseEventTests(unittest.TestCase):
    def test_random_emits_exactly_one_general_call(self):
        passengers, strategy, calibration = _population("random_front")
        events = release_events(
            passengers, strategy, release_schedule(passengers, strategy, calibration)
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "preparation_general_call")
        self.assertEqual(events[0].time_seconds, 0.0)
        self.assertIsNone(events[0].passenger_id)
        self.assertEqual(events[0].details["passenger_count"], len(passengers))

    def test_back_to_front_emits_one_call_per_zone(self):
        passengers, strategy, calibration = _population("back_to_front_zones")
        events = release_events(
            passengers, strategy, release_schedule(passengers, strategy, calibration)
        )
        self.assertEqual([event.type for event in events], ["preparation_zone_called"] * 6)
        self.assertEqual([event.time_seconds for event in events], [0.0, 20.0, 40.0, 60.0, 80.0, 100.0])
        self.assertEqual(sum(event.details["passenger_count"] for event in events), len(passengers))
        self.assertTrue(all(event.passenger_id is None for event in events))

    def test_strict_steffen_emits_one_call_per_passenger_in_order(self):
        passengers, strategy, calibration = _population("strict_steffen")
        events = release_events(
            passengers, strategy, release_schedule(passengers, strategy, calibration)
        )
        self.assertEqual(len(events), len(passengers))
        self.assertTrue(all(event.type == "preparation_passenger_called" for event in events))
        times = [event.time_seconds for event in events]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[-1], 716.0)
        self.assertTrue(all(event.passenger_id is not None for event in events))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_release -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'boarding_sim.release'`

- [ ] **Step 3: Add the release mode to strategies**

In `boarding_sim/strategies.py`, add a field to the `Strategy` dataclass after `companion_policy`:

```python
@dataclass(frozen=True)
class Strategy:
    id: str
    name: str
    access_recommended: str
    prep_cohorts: int
    cohort: Callable[[Passenger], int]
    rank: Callable[[Passenger, float], float]
    door: Callable[[Passenger], str]
    preserve_seat_door: bool = False
    companion_policy: str = "preserve"
    release_mode: str | None = None
```

Give `strict_steffen` its explicit mode by adding one keyword argument to its entry in `STRATEGIES`:

```python
    "strict_steffen": Strategy(
        "strict_steffen",
        "Strict Steffen · theoretical",
        "bridge",
        12,
        lambda p: _seat_group(p.seat) * 4 + (p.row % 2) * 2 + _side(p.seat),
        lambda p, _random_key: strict_steffen_rank(p),
        lambda _p: "front",
        companion_policy="separate",
        release_mode="individual",
    ),
```

Add the resolver below `strategy_complexity`:

```python
def strategy_release_mode(strategy: Strategy) -> str:
    """Resolve how the gate agent releases this strategy's passengers."""
    if strategy.release_mode:
        return strategy.release_mode
    return "general" if strategy.prep_cohorts <= 1 else "cohort"
```

- [ ] **Step 4: Add the calibration values**

In `config/behaviour-calibration.json`, add one entry after `"companionSeparationShock"`:

```json
  "preparationRelease": {"zoneIntervalSeconds": 20.0, "passengerIntervalSeconds": 4.0},
```

In `config/parameter-registry.json`, add two entries directly after the `behaviour.companionSeparationShock` line:

```json
  {"path":"behaviour.preparationRelease.zoneIntervalSeconds","value":20.0,"status":"UNCALIBRATED_HUMAN_BEHAVIOUR","category":"provisional","source":"Provisional gate-call assumption","note":"Interval between zone announcements; not an observed gate-agent rate. Requires Layer 4 calibration."},
  {"path":"behaviour.preparationRelease.passengerIntervalSeconds","value":4.0,"status":"UNCALIBRATED_HUMAN_BEHAVIOUR","category":"provisional","source":"Provisional gate-call assumption","note":"Interval between individual passenger calls; not an observed gate-agent rate. Requires Layer 4 calibration."},
```

- [ ] **Step 5: Write the release module**

Create `boarding_sim/release.py`:

```python
"""Gate-agent call schedule that makes passengers eligible to form the line.

Preparation has two distinct actions: a passenger becomes eligible after the
appropriate call, and only then does the behaviour model govern response,
walking, crowding, mistakes, correction and staging. This module owns the
first action. It is deterministic and consumes no random numbers.
"""

from __future__ import annotations

from typing import Any

from .models import Passenger, SimulationEvent
from .strategies import Strategy, strategy_release_mode


def _cohort_order(passengers: list[Passenger]) -> dict[int, int]:
    cohorts = sorted({passenger.prep_cohort for passenger in passengers})
    return {cohort: index for index, cohort in enumerate(cohorts)}


def release_schedule(
    passengers: list[Passenger],
    strategy: Strategy,
    calibration: dict[str, Any],
) -> dict[int, float]:
    """Return the time at which each passenger becomes eligible to move."""
    mode = strategy_release_mode(strategy)
    if mode == "general":
        return {passenger.id: 0.0 for passenger in passengers}

    intervals = calibration["preparationRelease"]
    if mode == "individual":
        interval = float(intervals["passengerIntervalSeconds"])
        return {
            passenger.id: round(passenger.boarding_rank * interval, 6)
            for passenger in passengers
        }

    interval = float(intervals["zoneIntervalSeconds"])
    order = _cohort_order(passengers)
    return {
        passenger.id: round(order[passenger.prep_cohort] * interval, 6)
        for passenger in passengers
    }


def release_events(
    passengers: list[Passenger],
    strategy: Strategy,
    schedule: dict[int, float],
) -> list[SimulationEvent]:
    """Return the gate-agent call events for this strategy at their modeled times."""
    mode = strategy_release_mode(strategy)
    if mode == "general":
        return [
            SimulationEvent(
                "preparation_general_call",
                0.0,
                None,
                {"passenger_count": len(passengers)},
            )
        ]

    if mode == "individual":
        ordered = sorted(passengers, key=lambda item: (schedule[item.id], item.id))
        return [
            SimulationEvent(
                "preparation_passenger_called", schedule[passenger.id], passenger.id
            )
            for passenger in ordered
        ]

    cohorts: dict[int, list[Passenger]] = {}
    for passenger in passengers:
        cohorts.setdefault(passenger.prep_cohort, []).append(passenger)
    return [
        SimulationEvent(
            "preparation_zone_called",
            schedule[members[0].id],
            None,
            {"cohort": cohort, "passenger_count": len(members)},
        )
        for cohort, members in sorted(cohorts.items())
    ]
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_release tests.test_foundation -v`
Expected: PASS. `tests.test_foundation` proves the two new registry entries cover the two new calibration leaves with matching values.

- [ ] **Step 7: Commit**

```bash
git add boarding_sim/release.py boarding_sim/strategies.py config/behaviour-calibration.json config/parameter-registry.json tests/test_release.py
git commit -m "feat: schedule gate-agent calls per boarding strategy"
```

---

### Task 2: Gate preparation on the call

**Files:**
- Modify: `boarding_sim/preparation.py` (`simulate_preparation`)
- Test: `tests/test_preparation.py`

**Interfaces:**
- Consumes: `release_schedule`, `release_events` from Task 1.
- Produces: `simulate_preparation` keeps its existing signature and `PreparationResult` shape. Its `events` list now also contains `preparation_general_call`, `preparation_zone_called` or `preparation_passenger_called`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_preparation.py`:

```python
class ControlledLineFormationTests(unittest.TestCase):
    def _run(self, strategy_id, seed=9107):
        scenario = normalize_scenario()
        scenario["preparation"]["policy"] = {
            "mode": "complete_preparation",
            "readinessTarget": 1.0,
            "firstCohortTarget": 1.0,
        }
        calibration = load_behaviour_calibration()
        strategy = strategy_by_id(strategy_id)
        rng = RNG(seed)
        passengers = generate_population(scenario, strategy, rng.fork(3), calibration)
        result = simulate_preparation(
            passengers, scenario, strategy, rng.fork(4), calibration
        )
        return passengers, result

    def test_uncalled_passengers_cannot_start_forming_the_line(self):
        passengers, result = self._run("strict_steffen")
        calls = {
            event.passenger_id: event.time_seconds
            for event in result.events
            if event.type == "preparation_passenger_called"
        }
        started = {
            event.passenger_id: event.time_seconds
            for event in result.events
            if event.type == "preparation_started"
        }
        self.assertTrue(started, "some passengers must respond to their call")
        for passenger_id, start_time in started.items():
            self.assertGreaterEqual(
                start_time,
                calls[passenger_id],
                f"passenger {passenger_id} moved before being called",
            )

    def test_strict_steffen_cannot_finish_before_its_final_call(self):
        _, result = self._run("strict_steffen")
        self.assertGreaterEqual(result.time_seconds, 716.0)

    def test_random_receives_one_general_call_and_no_other_calls(self):
        _, result = self._run("random_front")
        call_types = [
            event.type for event in result.events if event.type.startswith("preparation_") and "call" in event.type
        ]
        self.assertEqual(call_types, ["preparation_general_call"])

    def test_back_to_front_zones_are_called_twenty_seconds_apart(self):
        _, result = self._run("back_to_front_zones")
        times = [
            event.time_seconds
            for event in result.events
            if event.type == "preparation_zone_called"
        ]
        self.assertEqual(times, [0.0, 20.0, 40.0, 60.0, 80.0, 100.0])

    def test_calls_do_not_break_determinism(self):
        first = self._run("strict_steffen")[1]
        second = self._run("strict_steffen")[1]
        self.assertEqual(
            canonical_json_bytes(first.history), canonical_json_bytes(second.history)
        )
        self.assertEqual(first.time_seconds, second.time_seconds)
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_preparation.ControlledLineFormationTests -v`
Expected: FAIL — `test_uncalled_passengers_cannot_start_forming_the_line` fails because passengers currently move immediately, and `test_random_receives_one_general_call_and_no_other_calls` fails with an empty list.

- [ ] **Step 3: Wire the schedule into the preparation loop**

In `boarding_sim/preparation.py`, add the import beside the existing ones:

```python
from .release import release_events, release_schedule
```

In `simulate_preparation`, immediately after the existing `events = apply_companion_separation_shock(...)` line, add:

```python
    schedule = release_schedule(passengers, strategy, calibration)
    events.extend(release_events(passengers, strategy, schedule))
```

In the final decision branch of the per-passenger loop, insert the eligibility gate directly after the waiting-path `evolve_passenger` call and before the `utility = (` assignment:

```python
            evolve_passenger(
                passenger, dt, load_rate, recovery, calibration, threshold
            )
            if time_seconds < schedule[passenger.id]:
                continue
            utility = (
```

The gate sits after `evolve_passenger` on purpose: an uncalled passenger keeps accumulating frustration while waiting, which is the cost the previous model gave away for free. It sits before the activation draw so no random numbers are consumed on an ineligible passenger's behalf.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_preparation -v`
Expected: PASS, including the pre-existing policy, determinism and family-separation tests.

- [ ] **Step 5: Run the full Python suite**

Run: `python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: every test passes except `tests.test_default_artifact`, which fails because the tracked comparison artifact was built by the old model. Task 3 rebuilds it. If anything else fails, stop and investigate before continuing.

- [ ] **Step 6: Commit**

```bash
git add boarding_sim/preparation.py tests/test_preparation.py
git commit -m "feat: hold passengers at the gate until they are called"
```

---

### Task 3: Rebuild the default comparison

**Files:**
- Modify: `web/data/default-comparison.json` (regenerated, not hand-edited)
- Read: `scripts/build_default_comparison.py`

**Interfaces:**
- Consumes: the corrected model from Tasks 1 and 2.
- Produces: a regenerated 100-run artifact whose `representative` payload is what every later task quotes. No later task may quote a timing that is not read from this file.

- [ ] **Step 1: Rebuild the artifact**

Run: `python3 -m scripts.build_default_comparison --workers 4`
Expected: prints `Wrote N bytes to .../web/data/default-comparison.json`. This reruns 100 seeded comparisons and takes several minutes.

- [ ] **Step 2: Confirm no strategy timed out**

Run:

```bash
python3 - <<'PY'
import json
from scripts.build_default_comparison import load_default_artifact

artifact = load_default_artifact()
representative = artifact["representative"]
for strategy_id in representative["strategy_order"]:
    result = representative["strategies"][strategy_id]
    timings = result["metrics"]["timings_seconds"]
    aircraft = result["phases"]["part3_embarkation"]["aircraft"]
    experience = result["metrics"]["passenger_experience"]
    print(
        strategy_id,
        result["status"],
        "prep", round(timings["preparation"]),
        "entry", aircraft["first_entry_time_seconds"],
        "last_seat", aircraft["last_seat_time_seconds"],
        "total", timings["total_t0_to_last_seat"],
        "burden", round(experience["total_frustration_burden_f_minutes"]["mean"], 2),
    )
print("winner", representative["winner"])
print("valid runs", artifact["summary"]["run_records"].__len__())
PY
```

Expected: all three strategies report `valid`, and Strict Steffen's preparation is at least `716`. If any strategy is `timed_out`, STOP: do not raise `maxPreparationSeconds`. Report the timeout and its cause instead.

- [ ] **Step 3: Run the artifact test**

Run: `python3 -m unittest tests.test_default_artifact -v`
Expected: PASS.

- [ ] **Step 4: Run the full Python suite**

Run: `python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: all tests pass.

- [ ] **Step 5: Record the numbers**

Write the printed timings and burdens into the commit message body so the corrected result is recoverable from git history without rerunning the build.

- [ ] **Step 6: Commit**

```bash
git add web/data/default-comparison.json
git commit -m "data: rebuild the comparison with gate-agent calls"
```

---

### Task 4: Per-lane live frustration

**Files:**
- Modify: `web/index.html:77-81` (the `lane-key` block)
- Modify: `web/js/app.js` (`renderAt`, plus a new `updateLaneFrustration`)
- Modify: `web/race.css` (badge styling)
- Test: `tests/test_web_assets.py`, `tests/frustration-scale.test.mjs`

**Interfaces:**
- Consumes: `frustrationVisual(value, threshold)` from `web/js/frustration-scale.js`; `liveFrameAt(result, time)` already defined in `web/js/app.js`, whose frame index `1` is the serialized current mean frustration.
- Produces: DOM ids `lane-frustration-random_front`, `lane-frustration-back_to_front_zones`, `lane-frustration-strict_steffen`, each containing a whole-number percentage string such as `41%`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_web_assets.py` inside the existing test class that reads `web/index.html` (follow the surrounding style for locating the file):

```python
    def test_each_lane_shows_a_live_frustration_readout(self):
        markup = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")
        for strategy_id in ("random_front", "back_to_front_zones", "strict_steffen"):
            self.assertIn(f'id="lane-frustration-{strategy_id}"', markup)
        self.assertIn("model-predicted", markup)

    def test_lane_frustration_is_rendered_from_the_serialized_mean(self):
        script = (PROJECT_ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("updateLaneFrustration", script)
        self.assertIn("Math.round(frame[1] * 100)", script)
```

If `PROJECT_ROOT` is not already defined in that module, reuse whatever path constant the existing tests in the file use.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_web_assets -v`
Expected: FAIL with `'id="lane-frustration-random_front"' not found`.

- [ ] **Step 3: Add the readout to the markup**

Replace the `lane-key` block in `web/index.html` with:

```html
          <div class="lane-key" aria-hidden="true">
            <div>
              <strong>Random</strong><span>One loose queue</span>
              <p class="lane-frustration"><small>Frustration</small><output id="lane-frustration-random_front">0%</output></p>
            </div>
            <div>
              <strong>Back-to-front</strong><span>Six row zones</span>
              <p class="lane-frustration"><small>Frustration</small><output id="lane-frustration-back_to_front_zones">0%</output></p>
            </div>
            <div>
              <strong>Strict Steffen</strong><span>Theoretical sequence</span>
              <p class="lane-frustration"><small>Frustration</small><output id="lane-frustration-strict_steffen">0%</output></p>
            </div>
          </div>
```

The container stays `aria-hidden="true"`: the live table below remains the accessible source of the same numbers, matching the pattern already used for the canvas.

- [ ] **Step 4: Render the value**

In `web/js/app.js`, add above `renderAt`:

```javascript
function updateLaneFrustration(strategyId, result, time) {
  const element = byId(`lane-frustration-${strategyId}`);
  if (!element) return;
  const frame = liveFrameAt(result, time);
  if (!frame) {
    element.textContent = '—';
    return;
  }
  const value = frame[1];
  const visual = frustrationVisual(value, result.metrics.passenger_experience.threshold);
  element.textContent = `${Math.round(frame[1] * 100)}%`;
  element.style.color = visual.color;
}
```

Then call it inside `renderAt`'s existing loop:

```javascript
    for (const strategyId of comparison.strategy_order) {
      updateLiveRow(strategyId, comparison.strategies[strategyId], time);
      updateLaneFrustration(strategyId, comparison.strategies[strategyId], time);
    }
```

- [ ] **Step 5: Style the readout**

Append to `web/race.css`:

```css
.lane-frustration {
  display: flex;
  align-items: baseline;
  gap: .45rem;
  margin: .35rem 0 0;
}

.lane-frustration small {
  font-size: .62rem;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #8ea6c2;
}

.lane-frustration output {
  font-size: 1.45rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  color: #2e8b73;
}
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_web_assets -v && npm test`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/index.html web/js/app.js web/race.css tests/test_web_assets.py
git commit -m "feat: show live model-predicted frustration per lane"
```

---

### Task 5: Capture mode

**Files:**
- Create: `web/capture.css`
- Modify: `web/index.html` (link the stylesheet)
- Modify: `web/js/app.js` (read `capture`, `speed` and `autoplay` parameters)
- Test: `tests/test_web_assets.py`

**Interfaces:**
- Consumes: `createTimeline().setSpeed(value)`, which already accepts any positive number, and `timeline.play()`.
- Produces: `<body class="capture">` and `<body data-capture-stage="race" | "result">` when `?capture=1` is present; the page is byte-identical to today when it is absent.

- [ ] **Step 1: Write the failing tests**

Append to the same class in `tests/test_web_assets.py`:

```python
    def test_capture_mode_hides_controls_and_the_live_table(self):
        styles = (PROJECT_ROOT / "web" / "capture.css").read_text(encoding="utf-8")
        for selector in (
            ".capture .site-header",
            ".capture .clock-dock .playback-controls",
            ".capture .table-wrap",
            ".capture .passenger-inspector",
        ):
            self.assertIn(selector, styles)
        self.assertIn('[data-capture-stage="result"]', styles)

    def test_capture_mode_is_opt_in_by_query_parameter(self):
        script = (PROJECT_ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("applyCaptureMode", script)
        self.assertIn("'capture'", script)
        self.assertIn("'autoplay'", script)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m unittest tests.test_web_assets -v`
Expected: FAIL with `FileNotFoundError` for `web/capture.css`.

- [ ] **Step 3: Write the capture stylesheet**

Create `web/capture.css`:

```css
/* Recording layout. Applied only when the page is opened with ?capture=1. */

.capture {
  width: 1080px;
  min-height: 1350px;
  overflow: hidden;
}

.capture .site-header,
.capture .premise,
.capture .race-heading,
.capture .clock-dock .playback-controls,
.capture .table-wrap,
.capture .passenger-inspector,
.capture .scenario-section,
.capture .expert-section,
.capture .methodology-section,
.capture .share-section,
.capture .site-footer {
  display: none !important;
}

.capture .race-section {
  padding: 2rem 2.25rem;
}

.capture .clock-dock {
  justify-content: flex-start;
}

.capture .master-clock-wrap output {
  font-size: 4rem;
}

.capture .lane-key div strong {
  font-size: 1.35rem;
}

.capture .race-stage {
  height: 820px;
}

.capture[data-capture-stage="race"] .results-section {
  display: none !important;
}

.capture[data-capture-stage="result"] .race-stage,
.capture[data-capture-stage="result"] .clock-dock,
.capture[data-capture-stage="result"] .frustration-legend {
  display: none !important;
}

.capture[data-capture-stage="result"] .results-section {
  display: block;
  padding: 2.5rem 2.25rem;
}
```

Before writing this file, open `web/index.html` and confirm the class names used above match the real section classes. Where a class differs, use the real one — the selectors must actually match, and the tests only prove the file mentions them.

- [ ] **Step 4: Link the stylesheet**

In `web/index.html`, beside the existing `race.css` link:

```html
    <link rel="stylesheet" href="/capture.css">
```

- [ ] **Step 5: Apply the parameters**

In `web/js/app.js`, add above `applyQueryInputs`:

```javascript
function applyCaptureMode() {
  const parameters = new URLSearchParams(window.location.search);
  if (parameters.get('capture') !== '1') return {autoplay: false, speed: null};
  document.body.classList.add('capture');
  document.body.dataset.captureStage = 'race';
  const speed = Number(parameters.get('speed'));
  return {
    autoplay: parameters.get('autoplay') === '1',
    speed: Number.isFinite(speed) && speed > 0 ? speed : null,
  };
}
```

At the bottom of `installComparison`, after `renderAt(0)`, apply the capture settings:

```javascript
  const capture = captureSettings;
  if (capture.speed) timeline.setSpeed(capture.speed);
  if (capture.autoplay) {
    timeline.play();
    beginAnimation();
  }
```

Declare the settings once beside the other module-level state, near `let selectedPassenger = null;`:

```javascript
const captureSettings = applyCaptureMode();
```

Because `applyCaptureMode` is called at module scope, move its definition above that line.

- [ ] **Step 6: Verify the page by eye**

Run: `python3 -m boarding_sim --port 8791` in one shell, then open `http://127.0.0.1:8791/?capture=1&speed=20&autoplay=1`.
Expected: no header, no controls, no table; clock, three lanes with frustration percentages, and the legend visible. Then open `http://127.0.0.1:8791/` and confirm the normal page is unchanged. Stop the server with `Control-C`.

- [ ] **Step 7: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_web_assets -v && npm test`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add web/capture.css web/index.html web/js/app.js tests/test_web_assets.py
git commit -m "feat: add an opt-in recording layout"
```

---

### Task 6: Render the LinkedIn video

**Files:**
- Create: `scripts/record_linkedin_video.mjs`
- Create: `scripts/render_linkedin_video.sh`
- Create: `docs/media/` (holds the committed poster)
- Modify: `package.json` (add a `render:video` script)

**Interfaces:**
- Consumes: capture mode from Task 5 and the rebuilt artifact from Task 3.
- Produces: `output/boarding-frustration-linkedin.mp4` (1080×1350, H.264, yuv420p, 30 fps, `+faststart`) and `docs/media/boarding-frustration-poster.png`.

- [ ] **Step 1: Write the recorder**

Create `scripts/record_linkedin_video.mjs`:

```javascript
import {chromium} from '@playwright/test';
import {mkdir, rename, readdir} from 'node:fs/promises';
import {join} from 'node:path';

const baseURL = process.argv[2] ?? 'http://127.0.0.1:8791';
const outputDirectory = process.argv[3] ?? 'output';
const RACE_SECONDS = 34;
const RESULT_HOLD_MS = 6000;

await mkdir(outputDirectory, {recursive: true});
const browser = await chromium.launch({headless: true});
try {
  const context = await browser.newContext({
    viewport: {width: 1080, height: 1350},
    deviceScaleFactor: 1,
    recordVideo: {dir: outputDirectory, size: {width: 1080, height: 1350}},
  });
  const page = await context.newPage();
  await page.goto(`${baseURL}/?capture=1`);
  await page.waitForFunction(() => document.body.dataset.captureStage === 'race');
  const duration = await page.evaluate(async () => {
    const response = await fetch('/data/default-comparison.json');
    const artifact = await response.json();
    const representative = artifact.representative;
    return Math.max(
      ...representative.strategy_order.map((id) => representative.strategies[id].replay.ends_at_seconds),
    );
  });
  const speed = duration / RACE_SECONDS;
  console.log(JSON.stringify({duration_seconds: duration, playback_speed: speed}));

  await page.goto(`${baseURL}/?capture=1&autoplay=1&speed=${speed}`);
  await page.waitForFunction(
    () => document.getElementById('race-status')?.textContent?.startsWith('Ready'),
    null,
    {timeout: 120_000},
  );
  await page.waitForFunction(
    () => document.getElementById('master-clock').textContent !== '00:00',
    null,
    {timeout: 60_000},
  );
  await page.waitForFunction(
    (expected) => document.getElementById('timeline-scrubber').value >= expected,
    Math.floor(duration) - 1,
    {timeout: (RACE_SECONDS + 40) * 1000},
  );

  await page.evaluate(() => {
    document.body.dataset.captureStage = 'result';
  });
  await page.waitForTimeout(RESULT_HOLD_MS);
  await page.screenshot({path: join(outputDirectory, 'poster.png')});

  const video = page.video();
  await context.close();
  const source = await video.path();
  await rename(source, join(outputDirectory, 'race.webm'));
  console.log('recorded', await readdir(outputDirectory));
} finally {
  await browser.close();
}
```

- [ ] **Step 2: Write the wrapper**

Create `scripts/render_linkedin_video.sh` and make it executable:

```bash
#!/usr/bin/env bash
# Render the LinkedIn video from the tracked default comparison.
set -euo pipefail

PORT="${PORT:-8791}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="${ROOT}/output"

cd "${ROOT}"
rm -rf "${OUTPUT}"
mkdir -p "${OUTPUT}" docs/media

python3 -m boarding_sim --port "${PORT}" &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/config" >/dev/null 2>&1; then break; fi
  sleep 0.5
done

node scripts/record_linkedin_video.mjs "http://127.0.0.1:${PORT}" "${OUTPUT}"

ffmpeg -v error -y -i "${OUTPUT}/race.webm" \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 \
  -vf "scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2" \
  -movflags +faststart -an \
  "${OUTPUT}/boarding-frustration-linkedin.mp4"

cp "${OUTPUT}/poster.png" docs/media/boarding-frustration-poster.png

ffprobe -v error -show_entries format=duration -show_entries stream=width,height,codec_name \
  -of default=noprint_wrappers=1 "${OUTPUT}/boarding-frustration-linkedin.mp4"
```

Run: `chmod +x scripts/render_linkedin_video.sh`

- [ ] **Step 3: Add the npm script**

In `package.json`, inside `scripts`:

```json
    "render:video": "bash scripts/render_linkedin_video.sh",
```

- [ ] **Step 4: Render**

Run: `npm run render:video`
Expected: `ffprobe` reports `codec_name=h264`, `width=1080`, `height=1350`, and a duration near 40 seconds.

- [ ] **Step 5: Watch it**

Open `output/boarding-frustration-linkedin.mp4` and confirm: the clock runs from `00:00`, the long line-formation period is visible with Strict Steffen still forming while Random is already boarding, all three frustration percentages move, `model-predicted` is legible, and the closing result card is readable and held.

If any of those fail, fix the capture layout in Task 5's stylesheet and re-render before continuing.

- [ ] **Step 6: Commit**

```bash
git add scripts/record_linkedin_video.mjs scripts/render_linkedin_video.sh package.json docs/media/boarding-frustration-poster.png
git commit -m "feat: render the LinkedIn comparison video"
```

---

### Task 7: Research collection

**Files:**
- Create: `RESEARCH.md`
- Modify: `boarding_sim/server.py:32` (`PUBLIC_DOCUMENTS`)
- Modify: `web/index.html` (methodology section link)
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `SOURCES.md`, `VALIDATION_PLAN.md` and `config/parameter-registry.json` for the parameter-level detail it links to.
- Produces: `RESEARCH.md` served at `/RESEARCH.md`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_server.py`, following the request helper the existing tests in that file use:

```python
    def test_research_collection_is_public(self):
        status, _, body = self.request("GET", "/RESEARCH.md")
        self.assertEqual(status, 200)
        self.assertIn(b"Real-world observations", body)
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_server -v`
Expected: FAIL with status `404`.

- [ ] **Step 3: Research the real-world tier**

Use web search to establish what has actually been measured when these methods were tried. Cover at least:

- Schultz's field measurements at a real airport (already in `SOURCES.md`, restate what was observed rather than what was modelled);
- the Steffen and Hotchkiss mock-cabin experiment and the times it recorded;
- airline use of back-to-front and outside-in boarding and any published results;
- broadcast or independent replications.

Rules: every claim carries a citation to a checkable source, with the observed figure and the conditions it was measured under. Anything that cannot be sourced is omitted, not softened. Nothing in this tier is used to calibrate the model, and the document says so.

- [ ] **Step 4: Write the collection**

Create `RESEARCH.md` with exactly these top-level sections, in this order:

1. `# Research behind Boarding Lab` — one paragraph on what the experiment asks and what it does not claim.
2. `## How to read this document` — the four tiers and what weight each carries.
3. `## The boarding methods in plain language` — Random, Back-to-front, WILMA, Practical Steffen, Strict Steffen; two to four sentences each, no equations.
4. `## Tier 1 — Measured` — field-calibrated aircraft mechanics, with the specific parameter each source supports, linking to `SOURCES.md`.
5. `## Tier 2 — Research-informed structure` — delay tolerance, dynamic reference points, group behaviour, evolving impatience. Structure only; state explicitly that no coefficients are transferred.
6. `## Tier 3 — Assumptions of this model` — gate geometry, the 20-second zone interval, the 4-second individual call rate, preparation frustration coefficients, and the 0.25 companion-separation shock. Each row names the parameter-registry path and says what evidence would be needed to promote it.
7. `## Tier 4 — Real-world observations` — the researched trials, each with source, what was measured, and the conditions. Opens with a sentence stating these are context and are not used to calibrate this model.
8. `## What would change my mind` — the observations that would move a value out of tier 3.

- [ ] **Step 5: Serve it**

In `boarding_sim/server.py`:

```python
PUBLIC_DOCUMENTS = {"SOURCES.md", "VALIDATION_PLAN.md", "RESULT_SCHEMA.md", "RESEARCH.md"}
```

In the methodology section of `web/index.html`, add a link beside the existing document links:

```html
<a href="/RESEARCH.md">Research collection</a>
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_server tests.test_web_assets -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add RESEARCH.md boarding_sim/server.py web/index.html tests/test_server.py
git commit -m "docs: collect the papers, methods and field observations"
```

---

### Task 8: Prepare the repository for publication

**Files:**
- Create: `LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`
- Modify: `README.md`, `pyproject.toml`, `package.json`
- Move: `CODEX_PROMPT.md` → `docs/archive/CODEX_PROMPT.md`
- Move: `src/` → `reference/legacy-js/src/`, `tests/simulation.test.mjs` → `reference/legacy-js/tests/simulation.test.mjs`

**Interfaces:**
- Consumes: everything built in Tasks 1–7.
- Produces: a repository that runs from a fresh clone. No remote is added and nothing is pushed.

- [ ] **Step 1: Move the superseded prototype**

```bash
mkdir -p reference/legacy-js docs/archive
git mv src reference/legacy-js/src
mkdir -p reference/legacy-js/tests
git mv tests/simulation.test.mjs reference/legacy-js/tests/simulation.test.mjs
git mv CODEX_PROMPT.md docs/archive/CODEX_PROMPT.md
```

The relative import `../src/simulation.js` inside the moved test still resolves, because the test and the source moved together.

- [ ] **Step 2: Keep the moved test in the suite**

In `package.json`, change the test script so nothing drops out of the suite, and rename the project:

```json
  "name": "boarding-lab",
  "scripts": {
    "test": "node --test tests/*.test.mjs reference/legacy-js/tests/*.test.mjs",
```

Update `test:all` in the same file so its Node segment matches.

- [ ] **Step 3: Run both suites**

Run: `npm test && python3 -m unittest discover -s tests -p 'test_*.py'`
Expected: PASS, with the legacy prototype tests still running from their new location.

- [ ] **Step 4: Rename the Python project**

In `pyproject.toml`, set the project name to `boarding-lab`. Leave the package directory `boarding_sim` alone: renaming it would churn every import for no reader benefit.

- [ ] **Step 5: Add the licence**

Create `LICENSE` containing the standard MIT licence text with `Copyright (c) 2026 Dennis Kefalas`.

- [ ] **Step 6: Add the citation file**

Create `CITATION.cff`:

```yaml
cff-version: 1.2.0
message: "If you use this simulator, please cite it as below."
title: "Boarding Lab: a passenger-level aircraft boarding and frustration simulator"
abstract: >-
  A deterministic, passenger-by-passenger research simulator that models
  aircraft boarding from the gate preparation announcement to the final seated
  passenger, including model-predicted passenger frustration.
authors:
  - family-names: Kefalas
    given-names: Dennis
type: software
license: MIT
version: 0.3.0
date-released: "2026-08-14"
keywords:
  - aircraft boarding
  - discrete event simulation
  - passenger experience
```

- [ ] **Step 7: Add contributing notes**

Create `CONTRIBUTING.md` covering: how to run both suites, that Python is the single simulation authority and browser code renders only, and the rule that a value may not be relabelled from `provisional` to `calibrated` without validation evidence recorded in `VALIDATION_PLAN.md`.

- [ ] **Step 8: Rewrite the README for a stranger**

Rewrite `README.md` so it opens with what Boarding Lab is and the question it asks, shows `docs/media/boarding-frustration-poster.png`, then covers: quickstart, what is modelled, the evidence boundary with links to `RESEARCH.md` / `SOURCES.md` / `VALIDATION_PLAN.md`, the project map including `reference/legacy-js/`, the local API, how to rebuild the comparison and re-render the video, licence and citation.

State plainly, near the top, that gate-preparation and frustration outputs are model-predicted and provisional, and that the companion-separation shock is an assumption.

- [ ] **Step 9: Verify from a fresh clone**

```bash
CLONE="$(mktemp -d)/boarding-lab"
git clone . "${CLONE}"
cd "${CLONE}"
python3 -m unittest discover -s tests -p 'test_*.py'
npm install --silent && npm test
python3 -m boarding_sim --port 8799 &
sleep 3
curl -fsS http://127.0.0.1:8799/api/config >/dev/null && echo "server OK"
curl -fsS http://127.0.0.1:8799/RESEARCH.md >/dev/null && echo "research OK"
kill %1
cd -
```

Expected: both suites pass and both `OK` lines print. Fix anything that fails here — this is what a first visitor will hit.

- [ ] **Step 10: Confirm no remote exists**

Run: `git remote -v`
Expected: empty output. If a remote exists, remove it. Nothing is pushed.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "chore: prepare the repository for open-source publication"
```

---

## Self-Review

**Spec coverage:** Part 1 → Tasks 1–3. Part 2 → Tasks 4–5. Part 3 → Task 6. Part 4 → Task 7. Part 5 → Task 8. The spec's verification list maps as follows: uncalled-passenger gating, call ordering, Steffen lower bound, zone intervals and single general call → Task 2 Step 1; determinism → Task 2 Step 1; registry provenance → Task 1 Step 6; lane figure derivation → Task 4 Step 1; capture mode on and off → Task 5 Steps 1 and 6; MP4 dimensions and codec → Task 6 Step 4; manual video acceptance → Task 6 Step 5; fresh clone → Task 8 Step 9.

**Placeholder scan:** No TBD or TODO. Every code step carries real code. Task 7 Step 4 specifies section-by-section content rather than finished prose because its tier 4 depends on research performed in Step 3; the structure, ordering and sourcing rules are fully specified.

**Type consistency:** `strategy_release_mode`, `release_schedule` and `release_events` keep identical signatures between Task 1's interface block, its implementation, and Task 2's use. DOM ids `lane-frustration-<strategy_id>` are identical in Task 4's test, markup and script. `data-capture-stage` values `race` and `result` are identical across Task 5's stylesheet, Task 5's script and Task 6's recorder.

**Known risk:** Task 5 Step 3 writes selectors against class names read from `web/index.html`; the step instructs the implementer to confirm each against the real markup, because the tests only prove the selectors are present in the stylesheet, not that they match.
