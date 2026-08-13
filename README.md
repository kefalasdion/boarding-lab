# Passenger Boarding System Simulator

A deterministic, passenger-by-passenger research simulator for boarding an A320 with 180 seats.

The simulated clock starts at **T=0: the announcement to prepare for boarding**. It does not simulate airport arrival, check-in, security, shopping, or the earlier terminal journey. Delay, prior waiting, dwell, fatigue, trust, and connection pressure enter only as inputs used to create passenger state at T=0.

The application keeps three separate parts:

1. passenger state at T=0;
2. preparation required by the boarding method;
3. bridge or bus access and aircraft boarding until the final passenger is seated.

## Start the application

You need Python 3.11 or newer. No application packages need to be installed.

From this folder, run:

```bash
python3 -m boarding_sim
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080), then stop the server with `Control-C` when finished.

If port 8080 is already in use:

```bash
python3 -m boarding_sim --port 8765
```

## Run tests

The production Python suite is:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The original JavaScript reference tests remain available:

```bash
npm test
```

## Use the simulation package

Every run requires an explicit 32-bit integer seed.

```python
from boarding_sim import run_flight, run_monte_carlo

flight = run_flight(
    {"boarding": {"strategy": "wilma"}},
    seed=42,
)

comparison = run_monte_carlo(
    {"boarding": {"strategy": "wilma"}},
    runs=100,
    base_seed=10_000,
)
```

Use `boarding_sim.serialization.canonical_json_bytes(result)` when results must be compared or stored byte-for-byte. Dictionaries are key-sorted, separators are fixed, non-finite numbers are rejected, and Python's documented JSON floating-point representation is used.

## What is modeled

- correlated individual passenger traits and T=0 latent stress;
- families/groups as linked individual passengers;
- explicit strict-preparation readiness policy;
- passenger decisions, gate movement, staging, and correction events;
- separate boarding-control, bridge-walking, and door-headway events;
- bus allocation, loading, capacity, dispatch, stochastic travel, and two unloading streams;
- synchronous 0.4 m aircraft cells with one passenger per aisle cell;
- independent front and rear aircraft-door streams;
- seeded conflict resolution;
- field baggage/seat-interference service or the separate user occupancy rule;
- latent stress load and tolerance threshold as separate variables;
- initial and peak frustration, cumulative F·minutes, and time above a configurable threshold;
- deterministic Monte Carlo quantiles, 95% mean intervals, and valid/timeout/invalid counts.

## Evidence and validation status

This is a **research and calibration tool**, not a validated operational decision tool.

The aircraft boarding structure and selected inputs have published model support. Gate-preparation and passenger-frustration coefficients are provisional. Frustration outputs must not be described as validated until Layer 4 of [`VALIDATION_PLAN.md`](VALIDATION_PLAN.md) passes.

Every configurable value has a record in [`config/parameter-registry.json`](config/parameter-registry.json) with one of five display categories: calibrated, literature, user, operational, or provisional. Provisional human-behaviour coefficients live in [`config/behaviour-calibration.json`](config/behaviour-calibration.json), outside the engines, so they can later be fitted without rewriting physical boarding logic.

## Project map

- `boarding_sim/` — reusable deterministic Python simulation package;
- `web/` — rendering-only browser interface;
- `tests/` — Python unit, property/invariant, integration, API, and UI-contract tests;
- `config/default-scenario.json` — default scenario;
- `config/behaviour-calibration.json` — provisional human-behaviour layer;
- `config/parameter-registry.json` — provenance for every configurable leaf value;
- [`RESULT_SCHEMA.md`](RESULT_SCHEMA.md) — public result meanings;
- [`MODEL_SPEC.md`](MODEL_SPEC.md) — normative model specification;
- [`SOURCES.md`](SOURCES.md) — research sources and their permitted interpretation;
- `src/` — preserved JavaScript V2 executable reference prototype.

## Local JSON API

- `GET /api/config` — default scenario, strategies, provenance, and model status;
- `POST /api/run` — body `{ "scenario": {...}, "seed": 42 }`;
- `POST /api/monte-carlo` — body `{ "scenario": {...}, "runs": 100, "baseSeed": 10000 }`.

Scenario validation failures return HTTP 400 with stable `path`, `code`, and `message` issues. A simulation timeout is a successful HTTP response with `status: "timed_out"` because it is a modeled outcome.
