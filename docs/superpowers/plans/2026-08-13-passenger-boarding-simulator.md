# Passenger Boarding Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This checkout has no Git metadata, so commit steps are replaced by focused verification checkpoints.

**Goal:** Build a dependency-free Python simulation package and local browser UI that preserve the V2 boarding model boundary and expose deterministic, provenance-aware single-flight and Monte Carlo results.

**Architecture:** A typed Python package owns all model behavior and emits canonical JSON. A separate vanilla web interface calls a small standard-library HTTP API. Scenario, calibration, and provenance data remain external configuration with strict coverage checks.

**Tech Stack:** Python 3.11+ standard library, `unittest`, HTML5, CSS, vanilla JavaScript, SVG.

---

## File map

- `boarding_sim/*.py`: deterministic simulation package and server;
- `config/default-scenario.json`: normalized scenario with explicit readiness policy;
- `config/behaviour-calibration.json`: provisional behavior coefficients;
- `config/parameter-registry.json`: leaf-level provenance;
- `tests/test_*.py`: unit, property/invariant, integration, serialization, and API tests;
- `web/index.html`, `web/styles.css`, `web/app.js`: rendering-only browser application;
- `pyproject.toml`: package metadata without third-party dependencies;
- `README.md`: usage and validation-status documentation.

### Task 1: Deterministic configuration foundation

**Files:**
- Create: `boarding_sim/__init__.py`
- Create: `boarding_sim/prng.py`
- Create: `boarding_sim/validation.py`
- Create: `boarding_sim/provenance.py`
- Create: `boarding_sim/serialization.py`
- Create: `tests/test_foundation.py`
- Modify: `config/default-scenario.json`
- Create: `config/behaviour-calibration.json`
- Modify: `config/parameter-registry.json`

- [ ] Write failing tests for repeatable PRNG sequences, forked streams, strict scenario merging/rejection, canonical JSON bytes, and complete provenance coverage.

```python
def test_same_seed_produces_same_rng_sequence(self):
    self.assertEqual([RNG(42).next() for _ in range(1)], [RNG(42).next() for _ in range(1)])

def test_registry_covers_all_configurable_leaves(self):
    self.assertEqual(validate_registry_coverage(load_default_scenario(), load_calibration()), [])
```

- [ ] Run `python3 -m unittest tests.test_foundation -v` and confirm failures are caused by missing modules and configuration.
- [ ] Implement Mulberry32-compatible unsigned arithmetic, Box-Muller normal caching, exponential/Weibull/triangular helpers, deterministic shuffle/fork, path-stable validation issues, recursive strict merge, registry coverage, and canonical JSON encoding.
- [ ] Run the foundation tests and `python3 -m compileall -q boarding_sim`; expect success.

### Task 2: Typed passengers, strategies, and T=0 state

**Files:**
- Create: `boarding_sim/models.py`
- Create: `boarding_sim/frustration.py`
- Create: `boarding_sim/strategies.py`
- Create: `boarding_sim/population.py`
- Create: `tests/test_population_and_strategies.py`

- [ ] Write failing tests for 180 individual passengers, 180 unique seats, correlated-but-bounded traits, derived initial frustration, family contiguity, compatible cohorts, valid assigned doors, and threshold-time accumulation.

```python
def test_population_has_unique_individuals_and_seats(self):
    passengers = build_population(self.scenario, strategy_by_id("random_front"), RNG(9), self.calibration)
    self.assertEqual(len({p.id for p in passengers}), 180)
    self.assertEqual(len({(p.row, p.seat) for p in passengers}), 180)

def test_frustration_uses_tolerance_as_threshold_only(self):
    evolve_passenger(p, 60, load_rate_per_minute=.2, recovery_rate_per_minute=0, calibration=c)
    self.assertAlmostEqual(p.stress_load, before + .2)
```

- [ ] Run the focused test module and confirm expected failures.
- [ ] Implement dataclasses, strategy policies, Fisher-Yates rank keys, family graph assignments, companion compatibility, correlated latent-factor generation, initial load, and continuous experience tracking.
- [ ] Re-run the focused module and the foundation suite; expect success.

### Task 3: Strict preparation policy

**Files:**
- Create: `boarding_sim/preparation.py`
- Create: `tests/test_preparation.py`

- [ ] Write failing tests for explicit `strict_preparation`, both readiness targets, family-compatible preparation, progress samples, correction events, and preparation timeout.
- [ ] Run the focused preparation tests and confirm missing behavior fails.
- [ ] Implement `PreparationPolicy`, `StrictPreparationPolicy`, the preparation state machine, density slowdown, comprehension/correction logic, frustration integration, sampled progress, and modeled timeout output.
- [ ] Re-run preparation and population suites; expect success.

### Task 4: Event-based bridge and bus access

**Files:**
- Create: `boarding_sim/access.py`
- Create: `tests/test_access.py`

- [ ] Write failing tests proving bridge scan/walk/headway events, bus capacity allocation/loading/travel/unloading, assigned front/rear arrivals, deterministic access output, and no scalar bus penalty.
- [ ] Run access tests and confirm failures.
- [ ] Implement passenger access schedules, deterministic service draws, phase-state frustration integration, front/rear bus unloading streams, chronological progress history, and typed arrival results.
- [ ] Re-run access and prior suites; expect success.

### Task 5: Synchronous aircraft cellular automaton

**Files:**
- Create: `boarding_sim/aircraft.py`
- Create: `tests/test_aircraft.py`

- [ ] Write failing tests for exact custom load thresholds, field/custom separation, unique cell occupancy, adjacent moves only, direction toward the assigned row, both-door flow, deterministic conflict handling, target-row blocking, non-negative completion logic, and unique seating.

```python
def test_user_service_thresholds(self):
    self.assertEqual([custom_service_seconds(x, cfg) for x in (.59, .60, .70, .80, .90)], [15, 20, 25, 30, 35])

def test_movement_audit_has_no_teleportation(self):
    result = run_aircraft(...)
    self.assertTrue(all(abs(e.to_cell - e.from_cell) == 1 for e in result.movement_audit))
```

- [ ] Run aircraft tests and confirm expected failures.
- [ ] Implement target cells, row-service models, occupancy snapshots, movement credit, adjacent proposals, seeded conflict winners, simultaneous application, independent entry cells, row blocking, seating, and movement audit events.
- [ ] Re-run aircraft tests plus all earlier tests; expect success.

### Task 6: Flight orchestration, metrics, and result schema

**Files:**
- Create: `boarding_sim/metrics.py`
- Create: `boarding_sim/engine.py`
- Create: `tests/test_engine.py`

- [ ] Write failing tests for the three phase outputs, explicit seed requirement, byte-identical complete results, initial/peak/burden/time-above distributions, timing definitions, modeled timeout status, finite serialization, and no pre-T=0 simulated events.
- [ ] Run engine tests and confirm failures.
- [ ] Implement orchestration with named RNG forks, stable model/schema versions, provenance/status metadata, combined trajectories, passenger summaries, diagnostics, and canonical public dictionaries.
- [ ] Re-run engine and full suites; expect success.

### Task 7: Deterministic Monte Carlo

**Files:**
- Create: `boarding_sim/monte_carlo.py`
- Create: `tests/test_monte_carlo.py`

- [ ] Write failing tests for deterministic batches, `base_seed + index`, P10/P50/P90/P95 ranges, deterministic 95% mean intervals, valid/timeout/invalid counts, exclusion of unsuccessful runs, and `null` summaries when none are valid.
- [ ] Run Monte Carlo tests and confirm failures.
- [ ] Implement ordered sequential batches, stable run status records, summary extraction, finite empty handling, and confidence interval calculations.
- [ ] Re-run Monte Carlo and full suites; expect success.

### Task 8: Standard-library API server

**Files:**
- Create: `boarding_sim/server.py`
- Create: `boarding_sim/__main__.py`
- Create: `tests/test_server.py`
- Create: `pyproject.toml`

- [ ] Write failing tests for `GET /api/config`, `POST /api/run`, `POST /api/monte-carlo`, 400 validation responses, timeout-as-200 behavior, JSON content types, and traversal-safe static paths.
- [ ] Run server tests and confirm failures.
- [ ] Implement a `ThreadingHTTPServer` handler, bounded JSON-body parsing, API dispatch, safe static serving from `web/`, concise local error handling, and CLI host/port options.
- [ ] Re-run server and full suites; expect success.

### Task 9: Separate operational UI

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`
- Create: `tests/test_web_assets.py`

- [ ] Write failing asset-contract tests for required controls, phase sections, chart containers, distributions, uncertainty columns, provenance badges, timeout/invalid display, accessibility labels, and the absence of simulation formulas in UI JavaScript.
- [ ] Run web-asset tests and confirm failures.
- [ ] Implement the responsive scenario rail, three-part process view, SVG trajectories and histograms, progress/correction rendering, timing metrics, strategy Monte Carlo table, provenance table, warnings, loading/error states, keyboard focus, reduced-motion styles, and safe text rendering.
- [ ] Start the server, request `/`, `/api/config`, and a single `/api/run`, then re-run the asset and server suites.

### Task 10: Documentation and final verification

**Files:**
- Modify: `README.md`
- Create: `RESULT_SCHEMA.md`
- Create: `docs/IMPLEMENTATION_NOTES.md`
- Modify: `VERIFICATION_REPORT.md`

- [ ] Document installation-free startup, Python API examples, schema meanings, determinism limits, parameter provenance, strict-preparation semantics, and the four validation layers.
- [ ] Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` and confirm zero failures.
- [ ] Run `python3 -m compileall -q boarding_sim` and confirm exit code 0.
- [ ] Search simulation sources for forbidden randomness/current-clock seeding and confirm none exists.
- [ ] Execute one baseline bridge run, one two-door bus run, deterministic byte comparison, and a small Monte Carlo batch; record exact results in `VERIFICATION_REPORT.md`.
- [ ] Start the server and perform HTTP smoke requests for the page, config, flight, and Monte Carlo endpoints; stop it cleanly after the checks.
- [ ] Re-read `MODEL_SPEC.md`, `VALIDATION_PLAN.md`, and this plan against the implementation; record any intentionally documented differences before claiming completion.
