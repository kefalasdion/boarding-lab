# Boarding Lab Public Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a release-quality Boarding Lab experience that compares Random, Back-to-front, and theoretical Strict Steffen from scattered gate positions through preparation and final seating, with individual model-predicted frustration and an evidence-aware result.

**Architecture:** Keep Python as the only simulation authority. Refactor passenger creation so one seeded manifest can be cloned across strategies, add an authoritative two-dimensional gate/replay layer, and expose a compact three-strategy comparison API. Replace the current browser-first dashboard with a canvas-based synchronized race surrounded by semantic HTML results, accessibility fallbacks, methodology, and the existing expert analysis tools.

**Tech Stack:** Python 3.11+ standard library, deterministic dataclasses and JSON, vanilla ES modules, Canvas 2D, HTML/CSS, Node's built-in test runner, Python `unittest`, local `ThreadingHTTPServer`.

---

## File structure

### Python simulation

- `boarding_sim/population.py` — create strategy-neutral manifests, then apply a strategy to a clone.
- `boarding_sim/strategies.py` — add theoretical Strict Steffen and explicit companion policy metadata.
- `boarding_sim/gate.py` — gate geometry, seeded starting positions, queue-slot plans, collision-safe movement, and compact gate replay.
- `boarding_sim/preparation.py` — use gate plans, enforce public 100% readiness, and record authoritative preparation state.
- `boarding_sim/replay.py` — compose gate, access, aircraft, and passenger-frustration keyframes into a compact public replay.
- `boarding_sim/metrics.py` — preserve total frustration metrics and add exact preparation/embarkation burden distributions.
- `boarding_sim/engine.py` — expose an internal flight runner that accepts a cloned manifest while preserving `run_flight`.
- `boarding_sim/comparison.py` — run the three public strategies against one manifest and aggregate many-run comparisons.
- `boarding_sim/models.py` — focused dataclasses for gate/replay/comparison records.
- `boarding_sim/server.py` — public comparison endpoints and static-asset caching/security behavior.
- `boarding_sim/serialization.py` — keep comparison/replay JSON canonical and finite.

### Browser

- `web/index.html` — public race, result reveal, controls, methodology, and collapsed expert workspace.
- `web/styles.css` — global tokens, public composition, responsive layout, focus and reduced-motion behavior.
- `web/race.css` — gate/aircraft race, playback controls, inspector, and frustration legend.
- `web/expert.css` — detailed controls, charts, tables, and provenance surfaces.
- `web/js/app.js` — page orchestration only.
- `web/js/api.js` — config/comparison requests and structured error normalization.
- `web/js/timeline.js` — pure playback clock, seeking, speed, and replay-state lookup.
- `web/js/race-canvas.js` — allocation-conscious canvas renderer and hit testing.
- `web/js/frustration-scale.js` — value-to-color and value-to-accessible-label mapping only; no simulation formula.
- `web/js/results.js` — dynamic conclusion, timing breakdown, uncertainty, and heatmap rendering.
- `web/js/expert.js` — existing single-flight charts, Monte Carlo table, and provenance rendering.
- `web/js/share.js` — deterministic URL, copied summary, and 1200 × 627 result image.
- `web/data/default-comparison.json` — generated representative run and 100-run default summary.
- `scripts/build_default_comparison.py` — reproducibly regenerate the default artifact.

### Tests and documentation

- `tests/test_gate.py` — gate coordinates, queue definitions, movement, readiness, and determinism.
- `tests/test_comparison.py` — fair manifest cloning, public strategies, replay/result integrity, and many-run aggregation.
- `tests/test_server.py` — comparison endpoints, limits, security headers, and static default artifact.
- `tests/test_web_assets.py` — public semantic/accessibility/evidence contracts.
- `tests/timeline.test.mjs` — pure playback behavior.
- `tests/frustration-scale.test.mjs` — visual/accessibility scale boundaries.
- `tests/share.test.mjs` — deterministic URL and summary generation.
- `RESULT_SCHEMA.md`, `README.md`, `SOURCES.md`, `VERIFICATION_REPORT.md` — public contract, operation, evidence, and fresh verification.

## Task 1: Strategy-neutral manifest and theoretical Strict Steffen

**Files:**
- Modify: `boarding_sim/population.py`
- Modify: `boarding_sim/strategies.py`
- Modify: `boarding_sim/validation.py`
- Modify: `boarding_sim/models.py`
- Modify: `tests/test_population_and_strategies.py`

- [ ] **Step 1: Write failing tests for shared manifests and Strict Steffen**

Add tests that generate one strategy-neutral manifest, clone it, apply each public strategy, and compare stable passenger fields:

```python
def stable_passenger(passenger):
    return (
        passenger.id, passenger.row, passenger.seat, passenger.family_id,
        passenger.tolerance_threshold, passenger.walking_speed_mps,
        passenger.bag_count, passenger.initial_stress_load,
        passenger.initial_frustration,
    )

def test_public_strategies_use_identical_manifest(self):
    manifest = generate_manifest(self.scenario, RNG(20260813), self.calibration)
    populations = [
        assign_strategy(copy.deepcopy(manifest), strategy_by_id(strategy_id), RNG(77))
        for strategy_id in ("random_front", "back_to_front_zones", "strict_steffen")
    ]
    expected = [stable_passenger(passenger) for passenger in populations[0]]
    for population in populations[1:]:
        self.assertEqual([stable_passenger(passenger) for passenger in population], expected)

def test_strict_steffen_is_exact_and_may_separate_companions(self):
    passengers = assign_strategy(
        copy.deepcopy(generate_manifest(self.scenario, RNG(44), self.calibration)),
        strategy_by_id("strict_steffen"),
        RNG(91),
    )
    ordered = sorted(passengers, key=lambda passenger: passenger.boarding_rank)
    keys = [strict_steffen_key(passenger) for passenger in ordered]
    self.assertEqual(keys, sorted(keys))
    self.assertTrue(any(passenger.companion_override for passenger in passengers))
```

- [ ] **Step 2: Run the focused tests and confirm the missing API failure**

Run:

```bash
python3 -m unittest tests.test_population_and_strategies -v
```

Expected: failure because `generate_manifest`, `assign_strategy`, `strict_steffen_key`, and `strict_steffen` do not exist.

- [ ] **Step 3: Split manifest generation from strategy assignment**

Implement three public boundaries in `boarding_sim/population.py`. Rename the current `generate_population` body to `generate_manifest`, ending immediately after the existing passenger loop with `return passengers`. It must not receive or reference a `Strategy`. Add `assign_strategy(passengers, strategy, rng)` as the only call site for `apply_companion_policy(passengers, strategy, rng.fork(71))`. Rebuild `generate_population` as the compatibility wrapper `return assign_strategy(generate_manifest(scenario, rng, calibration), strategy, rng)`.

Move only the final strategy assignment out of the existing generator. Preserve byte-deterministic output for the existing `generate_population` entry point.

- [ ] **Step 4: Add explicit companion policies and Strict Steffen**

Extend `Strategy` with `companion_policy: str = "preserve"`. Add:

```python
def strict_steffen_key(passenger: Passenger) -> tuple[int, int, int, int]:
    return (
        _seat_group(passenger.seat),
        passenger.row % 2,
        _side(passenger.seat),
        -passenger.row,
    )

def strict_steffen_rank(passenger: Passenger) -> float:
    seat_group, parity, side, descending_row = strict_steffen_key(passenger)
    return float(
        seat_group * 100_000
        + parity * 10_000
        + side * 1_000
        + descending_row
    )

"strict_steffen": Strategy(
    id="strict_steffen",
    name="Strict Steffen · theoretical",
    access_recommended="bridge",
    prep_cohorts=12,
    cohort=lambda passenger: (
        _seat_group(passenger.seat) * 4
        + (passenger.row % 2) * 2
        + _side(passenger.seat)
    ),
    rank=lambda passenger, _random_key: strict_steffen_rank(passenger),
    door=lambda _passenger: "front",
    companion_policy="separate",
)
```

For `companion_policy == "separate"`, retain each member's theoretical slot and mark every member of a family spanning more than one queue slot/cohort with `companion_override=True`. Keep the existing `steffen_companion` behavior unchanged and rename only its display label to `Practical Steffen · companions together`.

- [ ] **Step 5: Validate the new strategy and preserve old behavior**

Add `strict_steffen` to `STRATEGY_IDS`. Run:

```bash
python3 -m unittest tests.test_population_and_strategies tests.test_engine -v
```

Expected: all tests pass, including existing family-contiguity tests for companion-compatible strategies.

- [ ] **Step 6: Commit the manifest/strategy slice**

```bash
git add boarding_sim/models.py boarding_sim/population.py boarding_sim/strategies.py boarding_sim/validation.py tests/test_population_and_strategies.py
git commit -m "feat: add fair manifests and strict Steffen"
```

## Task 2: Authoritative gate layout and queue plans

**Files:**
- Create: `boarding_sim/gate.py`
- Create: `tests/test_gate.py`
- Modify: `boarding_sim/models.py`
- Modify: `config/default-scenario.json`
- Modify: `config/parameter-registry.json`
- Modify: `boarding_sim/validation.py`

- [ ] **Step 1: Write failing geometry and queue-plan tests**

Cover unique seeded starts, bounded coordinates, unique targets, documented strategy grouping, and byte determinism:

```python
class GateLayoutTests(unittest.TestCase):
    def test_start_and_queue_positions_are_unique_and_bounded(self):
        plan = build_gate_plan(self.passengers, self.scenario, self.strategy, RNG(123))
        self.assertEqual(len(plan.start_positions), 180)
        self.assertEqual(len(set(plan.start_positions.values())), 180)
        self.assertEqual(len(set(plan.queue_slots.values())), 180)
        for point in (*plan.start_positions.values(), *plan.queue_slots.values()):
            self.assertGreaterEqual(point.x_m, 0)
            self.assertLessEqual(point.x_m, plan.layout.width_m)
            self.assertGreaterEqual(point.y_m, 0)
            self.assertLessEqual(point.y_m, plan.layout.height_m)

    def test_strict_steffen_slots_follow_exact_boarding_rank(self):
        plan = self.plan("strict_steffen")
        ordered_ids = [slot.passenger_id for slot in sorted(plan.slots, key=lambda slot: slot.slot_index)]
        expected_ids = [p.id for p in sorted(self.passengers_for("strict_steffen"), key=lambda p: p.boarding_rank)]
        self.assertEqual(ordered_ids, expected_ids)
```

- [ ] **Step 2: Run the test to confirm `boarding_sim.gate` is missing**

```bash
python3 -m unittest tests.test_gate -v
```

Expected: import failure for `boarding_sim.gate`.

- [ ] **Step 3: Add gate configuration with complete provenance**

Add to `preparation`:

```json
"gateAspectRatio": 1.6,
"passengerMarkerDiameterM": 0.45,
"queueLaneSpacingM": 0.75,
"replaySampleSeconds": 2
```

Register every leaf in `config/parameter-registry.json` as `USER_DEFINED_MODEL_POLICY` or `PROVISIONAL_OPERATIONAL`, with notes that geometry must be replaced by a target gate measurement before operational use. Extend strict validation for positive dimensions and `replaySampleSeconds` from 1 through 10.

- [ ] **Step 4: Define focused immutable gate records**

Add to `models.py`:

```python
@dataclass(frozen=True)
class GatePoint:
    x_m: float
    y_m: float

@dataclass(frozen=True)
class QueueSlot:
    passenger_id: int
    slot_index: int
    cohort: int
    point: GatePoint

@dataclass(frozen=True)
class GateLayout:
    width_m: float
    height_m: float
    boarding_control: GatePoint

@dataclass
class GatePlan:
    layout: GateLayout
    start_positions: dict[int, GatePoint]
    slots: list[QueueSlot]
    queue_slots: dict[int, GatePoint]
```

- [ ] **Step 5: Implement deterministic placement and serpentine queues**

In `gate.py`, compute `width = sqrt(area * aspect_ratio)` and `height = area / width`. Build a 0.75 m candidate grid, reserve the right-side boarding-control corridor for queue targets, and select unique start cells using `rng.shuffle`.

Implement one serpentine slot path for Random, six visibly separated five-row zone paths for Back-to-front, and one exact serpentine path ordered by `boarding_rank` for Strict Steffen. Slot order is data; browser code never derives it.

- [ ] **Step 6: Run geometry, registry, and strategy tests**

```bash
python3 -m unittest tests.test_gate tests.test_foundation tests.test_population_and_strategies -v
```

Expected: all tests pass; the registry covers every new configuration leaf.

- [ ] **Step 7: Commit the gate-plan slice**

```bash
git add boarding_sim/gate.py boarding_sim/models.py boarding_sim/validation.py config/default-scenario.json config/parameter-registry.json tests/test_gate.py
git commit -m "feat: model gate starts and queue plans"
```

## Task 3: Collision-safe gate preparation and strict public readiness

**Files:**
- Modify: `boarding_sim/gate.py`
- Modify: `boarding_sim/preparation.py`
- Modify: `boarding_sim/models.py`
- Modify: `tests/test_gate.py`
- Modify: `tests/test_preparation.py`

- [ ] **Step 1: Write failing movement, correction, and readiness tests**

Add assertions that sampled passenger positions are unique, adjacent samples obey the passenger speed bound plus one simulation-cell tolerance, every staged passenger ends at their assigned slot, and public readiness remains false at 179/180:

```python
def test_public_policy_requires_every_passenger(self):
    policy = CompletePreparationPolicy()
    for passenger in self.passengers[:-1]:
        passenger.prep_correct = True
    self.assertFalse(policy.evaluate(self.passengers).ready)
    self.passengers[-1].prep_correct = True
    self.assertTrue(policy.evaluate(self.passengers).ready)

def test_gate_frames_have_no_overlaps_or_teleportation(self):
    result = self.run_gate_preparation("strict_steffen")
    for frame in result.gate_replay.frames:
        points = [(state.x_m, state.y_m) for state in frame.passengers]
        self.assertEqual(len(points), len(set(points)))
    assert_gate_speed_bounds(result.gate_replay, self.passengers)
```

- [ ] **Step 2: Run focused tests and confirm missing complete policy/replay**

```bash
python3 -m unittest tests.test_gate tests.test_preparation -v
```

Expected: failures for `CompletePreparationPolicy` and missing `gate_replay`.

- [ ] **Step 3: Implement a complete-readiness policy without changing expert defaults**

Add `CompletePreparationPolicy` whose `ready` flag requires `all(passenger.prep_correct)`. Update `readiness_policy_from_config` to accept `mode="complete_preparation"`. The public comparison will override only:

```python
{"preparation": {"policy": {
    "mode": "complete_preparation",
    "readinessTarget": 1.0,
    "firstCohortTarget": 1.0,
}}}
```

Keep the existing single-flight expert default `strict_preparation` behavior and its tests.

- [ ] **Step 4: Evolve physical positions in the Python preparation loop**

Pass a `GatePlan` into `simulate_preparation`. Add per-passenger current point, target point, and movement progress to an internal gate state rather than to browser code. At each one-second preparation step:

1. take a position snapshot;
2. compute proposed movement toward the assigned slot using walking speed and crowd slowdown;
3. reject or offset proposals closer than the configured marker diameter;
4. resolve competing proposals with the seeded preparation RNG;
5. apply winners synchronously;
6. let correction events route a passenger to a unique correction bay before returning to their slot;
7. mark `prep_correct` only when the passenger reaches their assigned slot.

Record replay frames only every `replaySampleSeconds` plus all correction/staging transitions. Store rounded millimeter coordinates to keep canonical output compact and stable.

- [ ] **Step 5: Extend preparation results with authoritative replay**

Add:

```python
@dataclass(frozen=True)
class GatePassengerState:
    passenger_id: int
    x_m: float
    y_m: float
    state: str
    frustration: float
    frustration_burden: float

@dataclass(frozen=True)
class GateFrame:
    time_seconds: float
    passengers: list[GatePassengerState]

@dataclass
class GateReplay:
    layout: GateLayout
    slots: list[QueueSlot]
    frames: list[GateFrame]
```

Add `gate_replay: GateReplay` to `PreparationResult` and include it under `part2_preparation` serialization.

- [ ] **Step 6: Prove preparation remains deterministic and completes**

```bash
python3 -m unittest tests.test_gate tests.test_preparation tests.test_engine -v
```

Expected: Random, Back-to-front, and Strict Steffen prepare all 180 passengers without overlaps, and identical inputs produce identical replay bytes.

- [ ] **Step 7: Commit physical preparation**

```bash
git add boarding_sim/gate.py boarding_sim/models.py boarding_sim/preparation.py tests/test_gate.py tests/test_preparation.py
git commit -m "feat: simulate physical gate preparation"
```

## Task 4: Compact end-to-end replay and passenger frustration keyframes

**Files:**
- Create: `boarding_sim/replay.py`
- Modify: `boarding_sim/models.py`
- Modify: `boarding_sim/aircraft.py`
- Modify: `boarding_sim/preparation.py`
- Modify: `boarding_sim/metrics.py`
- Modify: `boarding_sim/engine.py`
- Modify: `tests/test_engine.py`
- Create: `tests/test_replay.py`

- [ ] **Step 1: Write failing replay integrity tests**

Test continuous time, traceability, finite values, sparse frustration frames, aircraft movement inclusion, and payload size:

```python
def test_replay_is_continuous_and_traces_every_passenger(self):
    result = to_primitive(run_flight({}, 5100))
    replay = result["replay"]
    self.assertEqual(replay["starts_at_seconds"], 0)
    self.assertEqual(replay["ends_at_seconds"], result["metrics"]["timings_seconds"]["total_t0_to_last_seat"])
    passenger_ids = {passenger["id"] for passenger in result["passengers"]}
    self.assertEqual(set(map(str, replay["passenger_tracks"])), set(map(str, passenger_ids)))
    self.assertLess(len(canonical_json_bytes(replay)), 2_500_000)
```

- [ ] **Step 2: Run replay tests and confirm missing replay output**

```bash
python3 -m unittest tests.test_replay -v
```

Expected: failure because `FlightResult` has no `replay`.

- [ ] **Step 3: Capture authoritative aircraft keyframes**

Keep the existing `MovementEvent` audit, but expose a compact replay stream containing `entered`, aisle-cell changes, `row_service_started`, and `seated`. Do not serialize the internal verbose movement audit twice.

At each configured replay sample, capture per-passenger frustration as `[passenger_id, rounded_value, rounded_burden, state_code]`. Each frame also carries the authoritative mean active frustration and mean accumulated passenger burden. The renderer may linearly interpolate between recorded values but may not calculate frustration or integrate burden.

- [ ] **Step 4: Compose phase tracks in `replay.py`**

Define a stable compact schema with a codebook:

```python
REPLAY_STATE_CODES = {
    "gate_waiting": 0, "gate_moving": 1, "gate_correcting": 2,
    "gate_staged": 3, "access_waiting": 4, "access_moving": 5,
    "aircraft_queue": 6, "aisle_moving": 7, "row_service": 8,
    "seated": 9,
}
```

The public JSON carries readable codebooks once and compact arrays thereafter. Include engine-produced driver labels such as `instruction_complexity`, `correction`, `waiting`, `crowding`, `aisle_blocked`, `row_service`, and `visible_progress`; the browser only displays labels present in the track.

- [ ] **Step 5: Attach replay to `FlightResult` without breaking existing metrics**

Add `replay: dict[str, Any]` to `FlightResult`, build it after the aircraft phase, increment schema/model versions, and update determinism expectations.

Extend `Passenger` with exact phase fields while preserving `frustration_burden` as the backward-compatible total:

```python
preparation_frustration_burden: float = 0.0
embarkation_frustration_burden: float = 0.0
```

Immediately after preparation ends, assign each passenger's current total burden to `preparation_frustration_burden`. After embarkation ends, assign:

```python
passenger.embarkation_frustration_burden = max(
    0.0,
    passenger.frustration_burden - passenger.preparation_frustration_burden,
)
```

Expose mean/P90 distributions in `metrics.passenger_experience` as `preparation_frustration_burden_f_minutes`, `embarkation_frustration_burden_f_minutes`, and `total_frustration_burden_f_minutes`. Keep the existing `frustration_burden_f_minutes` key as an alias of the total for compatibility.

Add this focused integrity test to `tests/test_engine.py`:

```python
def test_phase_burdens_partition_total_burden_exactly(self):
    result = run_flight({}, 5101)
    for passenger in result.passengers:
        self.assertAlmostEqual(
            passenger.preparation_frustration_burden
            + passenger.embarkation_frustration_burden,
            passenger.frustration_burden,
            places=10,
        )
    experience = result.metrics["passenger_experience"]
    self.assertEqual(
        experience["frustration_burden_f_minutes"],
        experience["total_frustration_burden_f_minutes"],
    )
```

- [ ] **Step 6: Run replay, engine, aircraft, and serialization tests**

```bash
python3 -m unittest tests.test_replay tests.test_engine tests.test_aircraft tests.test_foundation -v
```

Expected: all pass, all replay numbers finite, phase burdens partition the total, and the replay payload stays below the declared limit.

- [ ] **Step 7: Commit the replay slice**

```bash
git add boarding_sim/replay.py boarding_sim/models.py boarding_sim/preparation.py boarding_sim/aircraft.py boarding_sim/metrics.py boarding_sim/engine.py tests/test_replay.py tests/test_engine.py
git commit -m "feat: expose compact authoritative replay"
```

## Task 5: Fair three-strategy comparison and API

**Files:**
- Create: `boarding_sim/comparison.py`
- Modify: `boarding_sim/engine.py`
- Modify: `boarding_sim/__init__.py`
- Modify: `boarding_sim/server.py`
- Create: `tests/test_comparison.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing comparison and endpoint tests**

Cover shared manifests, required public strategies, no early boarding, dynamic winner behavior, timeout behavior, and stable endpoint shape:

```python
def test_public_comparison_uses_one_manifest_and_three_methods(self):
    result = to_primitive(run_comparison({}, 20260813))
    self.assertEqual(list(result["strategies"]), [
        "random_front", "back_to_front_zones", "strict_steffen"
    ])
    manifests = [run["manifest_fingerprint"] for run in result["strategies"].values()]
    self.assertEqual(len(set(manifests)), 1)
    for run in result["strategies"].values():
        prep_end = run["metrics"]["timings_seconds"]["preparation"]
        first_entry = run["phases"]["part3_embarkation"]["aircraft"]["first_entry_time_seconds"]
        self.assertGreaterEqual(first_entry, prep_end)
        self.assertEqual(run["phases"]["part2_preparation"]["readiness"]["overall"], 1.0)

def test_preparation_timeout_never_starts_access_or_declares_winner(self):
    result = to_primitive(run_comparison(
        {"preparation": {"maxPreparationSeconds": 1}}, 20260813
    ))
    self.assertIsNone(result["winner"])
    for run in result["strategies"].values():
        self.assertEqual(run["status"], "timed_out")
        self.assertEqual(run["phases"]["part3_embarkation"]["status"], "not_started")
        self.assertEqual(run["phases"]["part3_embarkation"]["access"]["events"], [])
        self.assertEqual(run["phases"]["part3_embarkation"]["aircraft"]["events"], [])
```

- [ ] **Step 2: Run focused tests and confirm missing comparison API**

```bash
python3 -m unittest tests.test_comparison tests.test_server -v
```

Expected: failures for missing `run_comparison` and `/api/compare`.

- [ ] **Step 3: Refactor an internal runner that accepts a cloned manifest**

In `engine.py`, keep public `run_flight` but introduce:

```python
def run_flight_from_manifest(
    scenario: dict[str, Any], seed: int, manifest: list[Passenger]
) -> FlightResult:
    validated_seed = validate_seed(seed)
    strategy = strategy_by_id(scenario["boarding"]["strategy"])
    passengers = assign_strategy(
        copy.deepcopy(manifest), strategy, RNG(validated_seed).fork(1)
    )
    return _run_assigned_flight(scenario, validated_seed, passengers, strategy)
```

Extract the existing preparation/access/aircraft/metrics/result construction into `_run_assigned_flight(scenario, validated_seed, passengers, strategy)`. Rebuild `run_flight` as normalization + `generate_manifest` + `_run_assigned_flight` so its public behavior remains compatible.

If preparation times out, `_run_assigned_flight` must return immediately through a focused `_preparation_timeout_result` builder. That result keeps the complete gate replay, uses `status="not_started"` for embarkation, empty access/aircraft events, `None` for unobserved timings, no seated passengers, and no call to either access or aircraft simulation.

Fingerprint only stable manifest fields using SHA-256 over canonical JSON. Never include strategy-derived rank/cohort fields in the fingerprint.

- [ ] **Step 4: Implement `run_comparison` and many-run aggregation**

`run_comparison` normalizes one common scenario, forces only complete preparation for the public race, preserves the selected common access mode, creates one manifest, runs the public strategy IDs in fixed order, and returns each full replay plus a winner only when all three runs are valid.

`run_comparison_monte_carlo` repeats the fair comparison for seeds `base_seed + index`, stores compact records, and aggregates the same timing/frustration/correction/separation metrics for each strategy. A failed strategy for one seed is counted and excluded only from that strategy's numeric summaries.

- [ ] **Step 5: Add bounded HTTP endpoints**

Implement:

- `POST /api/compare` with `{scenario, seed}`;
- `POST /api/compare-monte-carlo` with `{scenario, runs, baseSeed}` and `runs <= 200` for the interactive endpoint.

Retain `/api/run` and `/api/monte-carlo` for the expert workspace. Add `Content-Security-Policy`, `Referrer-Policy`, and `X-Frame-Options: SAMEORIGIN` headers without blocking local ES modules.

Wrap simulation endpoints in a module-level `threading.BoundedSemaphore(2)`. Acquire without waiting; return HTTP 503 `{ "error": "simulator_busy" }` when both slots are in use; always release in `finally`. The interactive comparison-Monte-Carlo endpoint rejects more than 200 runs even though the offline artifact builder may run larger batches.

- [ ] **Step 6: Run comparison/server tests**

```bash
python3 -m unittest tests.test_comparison tests.test_server tests.test_monte_carlo -v
```

Expected: all pass; validation is HTTP 400, modeled timeouts are HTTP 200, and three-strategy output is byte deterministic.

- [ ] **Step 7: Commit comparison orchestration**

```bash
git add boarding_sim/comparison.py boarding_sim/engine.py boarding_sim/__init__.py boarding_sim/server.py tests/test_comparison.py tests/test_server.py
git commit -m "feat: add fair public comparison API"
```

## Task 6: Public semantic shell and visual system

**Files:**
- Rewrite: `web/index.html`
- Rewrite: `web/styles.css`
- Create: `web/race.css`
- Create: `web/expert.css`
- Delete: `index.html`
- Modify: `package.json`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: Replace old asset-contract tests with the approved public contract**

Require IDs for `race-canvas`, `master-clock`, playback controls, strategy live regions, frustration legend, passenger inspector, result headline, timing table, heatmap, evidence disclosure, scenario controls, expert workspace, and sources. Assert the Adam Jacobs credit and exact `model-predicted` wording.

- [ ] **Step 2: Run the web contract test and confirm the old HTML fails it**

```bash
python3 -m unittest tests.test_web_assets -v
```

Expected: failures for missing public-race and result elements.

- [ ] **Step 3: Build the semantic document structure**

Use one `h1`, a concise premise, an immediate race section, a results section, a scenario section, a collapsed expert `details`, and methodology/sources footer. Provide a `table` fallback summarizing each strategy's phase, prepared/entered/seated counts, live mean frustration, preparation-finished time, boarding-started time, boarding-finished time, preparation burden, embarkation burden, and total burden.

The canvas has an accessible name but is `aria-hidden="true"` when the live table is present, preventing duplicate noisy announcements. Status changes are summarized in restrained `aria-live="polite"` text.

Remove the obsolete root `index.html` entry point and change `npm run serve` to invoke `python3 -m boarding_sim`. The preserved `src/` JavaScript reference remains testable but is no longer a second runnable application.

- [ ] **Step 4: Implement the approved restrained visual system**

Define CSS variables for warm neutral, navy, action blue, and the five frustration colors. Desktop uses three horizontal lanes. At `max-width: 780px`, the race becomes three stacked lane regions under a sticky clock and the result cards become a single comparison table/list.

Add visible focus, 44 px touch targets, `prefers-reduced-motion`, forced-colors support, and print/social-capture rules. Keep the live race as the dominant visual; do not reintroduce dashboard-card mosaics.

- [ ] **Step 5: Run web contracts and HTML smoke checks**

```bash
python3 -m unittest tests.test_web_assets -v
python3 -m boarding_sim --port 8765
```

Open `http://127.0.0.1:8765` and confirm the shell loads before JavaScript results arrive, headings are meaningful, and the mobile document does not horizontally scroll.

- [ ] **Step 6: Commit the public shell**

```bash
git add web/index.html web/styles.css web/race.css web/expert.css package.json tests/test_web_assets.py
git add -u index.html
git commit -m "feat: build Boarding Lab public shell"
```

## Task 7: Playback state and canvas race

**Files:**
- Create: `web/js/api.js`
- Create: `web/js/timeline.js`
- Create: `web/js/frustration-scale.js`
- Create: `web/js/race-canvas.js`
- Create: `web/js/app.js`
- Create: `tests/timeline.test.mjs`
- Create: `tests/frustration-scale.test.mjs`
- Modify: `package.json`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: Write failing pure JavaScript tests**

Test clamping, pause/play, seek, speed, end behavior, reduced-motion stepping, frustration color boundaries, and accessible labels:

```javascript
test('clock advances according to speed and clamps at duration', () => {
  const timeline = createTimeline({duration: 100, speed: 2});
  timeline.play();
  timeline.advance(12);
  assert.equal(timeline.time(), 24);
  timeline.advance(100);
  assert.equal(timeline.time(), 100);
  assert.equal(timeline.playing(), false);
});

test('high threshold has a non-color label and ring flag', () => {
  assert.deepEqual(frustrationVisual(0.75), {
    color: '#bd315e', label: 'High', aboveThreshold: true,
  });
});
```

- [ ] **Step 2: Run Node tests and confirm missing modules**

```bash
npm test
```

Expected: module-not-found failures for the new browser modules.

- [ ] **Step 3: Implement API and pure timeline modules**

`api.js` performs JSON requests, converts structured validation issues into field messages, and distinguishes modeled timeouts from network failures. `timeline.js` contains no DOM access and exposes `play`, `pause`, `seek`, `setSpeed`, `advance`, `time`, and `playing`.

- [ ] **Step 4: Implement the frustration display scale**

Map only already-computed values to the approved five-color ramp and labels. Keep the threshold value supplied by result data. Do not import, copy, or derive the sigmoid or any behavior coefficient.

- [ ] **Step 5: Implement one allocation-conscious race canvas**

`race-canvas.js`:

- measures logical regions from the DOM-provided canvas rectangle;
- draws gate, queue, transfer indicator, aircraft, and 540 passenger marks;
- interpolates between authoritative replay keyframes;
- keeps reusable typed arrays for passenger screen positions and colors;
- performs hit testing against the latest position array;
- caps device pixel ratio at 2;
- stops `requestAnimationFrame` while paused or hidden;
- emits selected passenger IDs to `app.js` without owning inspector HTML.

The renderer may interpolate coordinates and frustration values between recorded samples. It may not derive queue slots, passenger states, timing, frustration, or winner status.

- [ ] **Step 6: Wire playback, live text, inspector, and reduced motion**

`app.js` loads the default comparison, updates the shared clock, controls, live strategy summary, and passenger inspector. Each lane reads its serialized frame aggregates and displays `Math.round(mean_frustration * 100)` as the live `0–100` index plus serialized mean accumulated F·minutes beneath it. It must never integrate burden in JavaScript. In reduced-motion mode, seeking jumps between event times and no pulse/continuous movement runs.

- [ ] **Step 7: Run JavaScript, web-contract, and syntax tests**

```bash
npm test
node --check web/js/app.js
node --check web/js/race-canvas.js
python3 -m unittest tests.test_web_assets -v
```

Expected: all pass and `Math.random`, `sigmoid`, `weibull`, and strategy ranking remain absent from browser production code.

- [ ] **Step 8: Commit the race renderer**

```bash
git add web/js package.json tests/timeline.test.mjs tests/frustration-scale.test.mjs tests/test_web_assets.py
git commit -m "feat: animate the continuous boarding race"
```

## Task 8: Dynamic results, expert workspace, and sharing

**Files:**
- Create: `web/js/results.js`
- Create: `web/js/expert.js`
- Create: `web/js/share.js`
- Create: `tests/share.test.mjs`
- Modify: `web/js/app.js`
- Modify: `web/index.html`
- Modify: `web/styles.css`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: Write failing result/share tests**

Test no-winner behavior, deterministic query parameters, model-predicted wording, and share summary content:

```javascript
test('share URL preserves seed and public scenario inputs', () => {
  const url = resultUrl('https://example.test/lab', {seed: 42, delayMinutes: 20});
  assert.equal(url, 'https://example.test/lab?seed=42&delay=20');
});

test('timed-out comparisons do not declare a winner', () => {
  assert.equal(conclusionFor({strategies: {a: {status: 'timed_out'}}}).winner, null);
});
```

- [ ] **Step 2: Run Node/web tests and confirm missing result modules**

```bash
npm test
python3 -m unittest tests.test_web_assets -v
```

Expected: failures for missing modules/contracts.

- [ ] **Step 3: Render evidence-aware dynamic results**

`results.js` renders the server-provided conclusion and ranking only if all strategies are valid. It separately shows preparation finished at, boarding started at, boarding finished at, preparation duration, access, cabin, total, corrections, companion separations, frustration accumulated during preparation, frustration accumulated during embarkation, total frustration burden, peak, threshold share, P10–P90, confidence interval, and run counts. Missing summaries display `Unavailable`, never `0`.

Use only authoritative timestamps already present in each run: `metrics.timings_seconds.preparation`, `phases.part3_embarkation.aircraft.first_entry_time_seconds`, and `phases.part3_embarkation.aircraft.last_seat_time_seconds`. Labels say “accumulated during,” never “caused by,” and every frustration result remains visibly `model-predicted` and `provisional`.

Render peak/burden cabin heatmaps from per-passenger results and maintain a real table with the same data for keyboard and screen-reader users.

- [ ] **Step 4: Preserve the existing expert value in a focused module**

Move the useful chart/table/provenance functions from the old `web/app.js` into `expert.js`. Keep single-flight strategy controls, preparation/embarkation trajectories, burden/peak histograms, Monte Carlo table, and parameter provenance. Do not keep the old page composition or duplicate public-race controls.

- [ ] **Step 5: Implement deterministic sharing**

`share.js` uses an allowlist of scenario query parameters, copies a plain-language summary that includes `model-predicted`, and draws a 1200 × 627 image containing Boarding Lab, `By Dennis Kefalas`, three total-time bars, preparation insight, seed/model version, and evidence caveat. Export with `canvas.toBlob` and a user-triggered download.

- [ ] **Step 6: Run tests and manually inspect incomplete results**

```bash
npm test
python3 -m unittest tests.test_web_assets -v
```

Use a one-second preparation or boarding limit through the API and confirm the result keeps completed strategies visible, marks the timeout, and omits a winner.

- [ ] **Step 7: Commit results and sharing**

```bash
git add web/js/results.js web/js/expert.js web/js/share.js web/js/app.js web/index.html web/styles.css tests/share.test.mjs tests/test_web_assets.py
git commit -m "feat: reveal and share evidence-aware results"
```

## Task 9: Reproducible default comparison artifact

**Files:**
- Create: `scripts/build_default_comparison.py`
- Create: `web/data/default-comparison.json`
- Modify: `boarding_sim/server.py`
- Modify: `tests/test_server.py`
- Create: `tests/test_default_artifact.py`

- [ ] **Step 1: Write failing artifact integrity tests**

Require the artifact's schema/model version, representative replay seed, fixed public strategy order, 100 requested runs per strategy, no fabricated winner, and canonical regeneration:

```python
def test_default_artifact_is_current_and_reproducible(self):
    artifact = load_default_artifact()
    self.assertEqual(artifact["model_version"], MODEL_VERSION)
    self.assertEqual(artifact["summary"]["requested_runs"], 100)
    self.assertEqual(list(artifact["representative"]["strategies"]), PUBLIC_STRATEGY_IDS)
    self.assertEqual(canonical_json_bytes(artifact), build_default_artifact())
```

- [ ] **Step 2: Run the artifact test and confirm the file/builder is missing**

```bash
python3 -m unittest tests.test_default_artifact -v
```

Expected: import/file-not-found failure.

- [ ] **Step 3: Implement deterministic artifact generation**

Use base seed `20260813`, 100 fair comparisons, and select the representative seed whose three normalized total times have the smallest squared distance from their respective medians. Write canonical JSON through `canonical_json_bytes`; never use wall time or random sampling.

The artifact contains one full replay and the compact 100-run summary, not all 100 replays.

- [ ] **Step 4: Generate and validate the tracked artifact**

```bash
python3 scripts/build_default_comparison.py
python3 -m unittest tests.test_default_artifact -v
```

Expected: pass and `web/data/default-comparison.json` is finite canonical JSON.

- [ ] **Step 5: Serve generated data with appropriate caching**

Keep API responses `no-store`. Serve versioned files under `/data/` with `Cache-Control: public, max-age=3600` and `ETag` based on content SHA-256. Preserve path-traversal protection.

- [ ] **Step 6: Commit the default artifact**

```bash
git add scripts/build_default_comparison.py web/data/default-comparison.json boarding_sim/server.py tests/test_default_artifact.py tests/test_server.py
git commit -m "feat: ship reproducible default comparison"
```

## Task 10: Documentation and release-grade verification

**Files:**
- Modify: `README.md`
- Modify: `RESULT_SCHEMA.md`
- Modify: `SOURCES.md`
- Modify: `VALIDATION_PLAN.md`
- Rewrite: `VERIFICATION_REPORT.md`
- Modify: `docs/IMPLEMENTATION_NOTES.md`
- Create: `playwright.config.mjs`
- Create: `tests/web-experience.spec.mjs`
- Create: `tests/smoke_standalone.sh`
- Modify: `package.json`
- Modify: `package-lock.json`

- [ ] **Step 1: Update public and developer documentation**

Document:

- `python3 -m boarding_sim` start instructions;
- the public three-way comparison and expert workspace;
- `/api/compare` and `/api/compare-monte-carlo`;
- replay codebooks, frames, and traceability;
- exact phase-burden fields, their additive integrity rule, and the distinction between time attribution and causation;
- Adam Jacobs inspiration credit and distinction from his boarding-only clock;
- published aircraft inputs versus provisional preparation/frustration values;
- regeneration of the default artifact;
- the explicit deferral of FlyByCode integration, deployment, and LinkedIn publication.

- [ ] **Step 2: Add pinned browser and accessibility verification**

Add `@playwright/test` and `@axe-core/playwright` as development-only dependencies. Configure Playwright's `webServer` to start `python3 -m boarding_sim --port 8765`, use `http://127.0.0.1:8765`, collect traces on first retry, and run Chromium desktop plus a 390 × 844 mobile project. The browser suite covers default autoload, synchronized lanes, all playback controls, no clock reset, passenger selection, timeout/no-winner behavior, reduced motion, keyboard flow, share download, zero console/page/request errors, and an axe scan with zero serious or critical findings.

Add scripts:

```json
"test:e2e": "playwright test",
"test:all": "python3 -m unittest discover -s tests -p 'test_*.py' -v && node --test tests/*.test.mjs && playwright test"
```

- [ ] **Step 3: Add a clean-archive standalone smoke test**

`tests/smoke_standalone.sh` must start the Python server on an ephemeral port from the extracted archive, wait for `/api/config`, verify `/`, `/data/default-comparison.json`, and one live `/api/run`, then stop the server through a cleanup trap. It must require only Python 3.11+ at runtime.

- [ ] **Step 4: Extend server security regression coverage**

Add tests for encoded traversal variants, oversized/missing/invalid `Content-Length`, malformed UTF-8/JSON, wrong HTTP methods, unknown API routes, invalid seed/run counts, interactive run cap, busy semaphore behavior, and security headers. Keep loopback as the documented default and do not describe the built-in server as internet-facing production hosting.

- [ ] **Step 5: Run the complete automated suite once**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
npm test
 npm run test:e2e
python3 -m compileall -q boarding_sim scripts
node --check web/js/app.js
```

Expected: all Python and JavaScript tests pass; compile/syntax commands exit 0.

- [ ] **Step 6: Run deterministic and safety audits**

```bash
rg -n 'import random|from random|Math\.random|Date\.now\(.*seed|time\.time\(.*seed' boarding_sim web scripts
python3 scripts/build_default_comparison.py
git diff --exit-code -- web/data/default-comparison.json
```

Expected: no forbidden randomness/clock seeding, and artifact regeneration creates no diff.

- [ ] **Step 7: Perform real-browser desktop verification**

Start the server on an unused port. Verify at a desktop viewport:

- scattered passengers visibly form three different queues;
- Random can board while Strict Steffen is preparing;
- colors change from engine keyframes;
- hover/tap inspector matches the selected passenger's serialized data;
- pause, replay, seek, and 0.5×/1×/2×/4× work;
- each lane shows a different authoritative preparation/boarding transition when the strategies finish preparation at different times;
- preparation-finished, boarding-started, and boarding-finished timestamps match the API values;
- live frustration is a `0–100` current index while preparation, embarkation, and total burden are labeled in F·minutes;
- result headline and winner match the many-run data;
- peak/burden heatmap switches;
- methodology, sources, and inspiration links work;
- expert charts and tables render;
- no console errors occur.

- [ ] **Step 8: Perform phone, accessibility, and reduced-motion verification**

At 390 × 844:

- no horizontal overflow;
- clock remains visible while lanes stack;
- canvas and controls remain legible/tappable;
- keyboard traverses every control with visible focus;
- passenger information and strategy state are available without canvas/color;
- forced reduced motion uses event steps and no pulsing;
- a screen-reader-oriented accessibility-tree inspection has meaningful names and no duplicate canvas announcements.

- [ ] **Step 9: Measure playback and payload budgets**

Record in `VERIFICATION_REPORT.md`:

- default artifact byte size;
- `/api/compare` response size;
- default comparison generation duration;
- 100-run artifact generation duration;
- 30-second canvas playback median and P95 frame time with 540 marks;
- maximum long frame and visible dropped-frame symptoms.

Acceptance targets: representative replay below 2.5 MB uncompressed, default artifact below 4 MB, steady playback median below 16.7 ms and P95 below 33.3 ms on Dennis's MacBook Air, no sustained stutter, and responsive controls throughout.

- [ ] **Step 10: Verify modeled timeout and error resilience**

Use API test scenarios with one-second preparation and boarding limits. Confirm no fabricated zeros, no overall winner, preserved completed results, readable validation messages, and successful retry.

- [ ] **Step 11: Verify a clean source archive**

```bash
archive_dir=$(mktemp -d)
git archive HEAD | tar -x -C "$archive_dir"
(cd "$archive_dir" && bash tests/smoke_standalone.sh)
```

Expected: the public page, default artifact, config API, and live run all work without Node, network, a database, or package installation.

- [ ] **Step 12: Write the fresh verification report and commit release state**

Include exact commands, counts, measured values, browser viewport results, known scientific limits, and the statement that this verifies software quality rather than operational validity.

```bash
git add README.md RESULT_SCHEMA.md SOURCES.md VALIDATION_PLAN.md VERIFICATION_REPORT.md docs/IMPLEMENTATION_NOTES.md playwright.config.mjs tests/web-experience.spec.mjs tests/smoke_standalone.sh package.json package-lock.json
git commit -m "docs: verify Boarding Lab release candidate"
git status --short
```

Expected: clean worktree and no uncommitted generated artifacts.

## Task 11: Independent final review

**Files:**
- Review only unless a finding requires a focused fix.

- [ ] **Step 1: Run specification-compliance review**

Give a fresh reviewer the approved design spec, this plan, and the final diff. Require a requirement-by-requirement verdict for fair manifests, gate-to-queue flow, continuous clock, individual frustration, evidence labels, result hierarchy, accessibility, and scope limits.

- [ ] **Step 2: Run code-quality and security review**

Review deterministic boundaries, replay traceability, payload limits, server input limits/path security, canvas allocation behavior, failure states, and absence of duplicated simulation rules in JavaScript.

- [ ] **Step 3: Fix only validated findings and rerun affected checks**

For each accepted finding, add or tighten a regression test, make the focused fix, run the narrow test, then rerun the complete suites once after all fixes.

- [ ] **Step 4: Tag the standalone completion point**

```bash
git tag -a boarding-lab-standalone-v1 -m "Boarding Lab standalone v1"
git status --short
```

Expected: tag created on a clean, verified commit. FlyByCode integration and LinkedIn publication remain outside this tag and require their own approved plan.
