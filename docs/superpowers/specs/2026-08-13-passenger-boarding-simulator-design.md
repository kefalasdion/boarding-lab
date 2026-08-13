# Passenger Boarding Simulator Production Design

**Date:** 2026-08-13  
**Status:** Approved for implementation  
**Model authority:** `MODEL_SPEC.md`, `config/parameter-registry.json`, `VALIDATION_PLAN.md`, `CHANGELOG_V1_TO_V2.md`, and `SOURCES.md`

## Purpose and boundary

Build a reusable, deterministic passenger-boarding simulation package and a local browser interface. The simulated clock starts at the announcement to prepare for boarding. Earlier airport experience is represented only by initial-condition inputs that create each passenger's latent stress load at T=0.

The result always preserves three separately reported parts:

1. passenger state at T=0;
2. preparation required by the selected boarding method;
3. embarkation through bridge or bus, the aircraft door or doors, the cabin aisle, row service, and final seating.

The application is a research and calibration tool. It must not describe provisional frustration outputs as validated passenger psychology.

## Chosen implementation

Use Python 3.11 or newer for the simulation package and test suite. Use only the Python standard library. Serve a separate vanilla HTML, CSS, and JavaScript interface through a small local HTTP/JSON server supplied by the package.

This avoids a second simulation implementation in the browser, keeps the deterministic Python package as the single executable source of truth, and requires no framework installation.

## Package boundaries

The `boarding_sim` package contains focused modules:

- `models.py`: typed dataclasses and enums for passengers, events, phase outputs, metrics, and run results;
- `validation.py`: strict scenario validation, default merging, and structured validation errors;
- `prng.py`: fixed seeded pseudo-random generator and named distribution methods;
- `provenance.py`: parameter-registry loading, coverage validation, and UI badge categories;
- `population.py`: correlated passenger generation and T=0 state;
- `strategies.py`: boarding policy definitions and family-compatible cohort/rank/door assignment;
- `frustration.py`: latent-load mapping and state integration using provisional calibration values;
- `preparation.py`: readiness policy interface and strict-preparation engine;
- `access.py`: event-based bridge and bus processes;
- `aircraft.py`: synchronous 0.4 m-cell aircraft cellular automaton;
- `metrics.py`: passenger distributions, phase metrics, trajectories, and canonical result construction;
- `monte_carlo.py`: deterministic repeated runs and valid/timeout/invalid aggregation;
- `engine.py`: public `run_flight` orchestration entry point;
- `serialization.py`: canonical, finite JSON encoding for byte-equivalent results;
- `server.py` and `__main__.py`: local static/API server and command-line entry point.

Rendering code in `web/` may consume serialized results but may not import, reproduce, or alter simulation rules.

## Configuration, calibration, and provenance

`config/default-scenario.json` remains the human-editable default scenario. Strict preparation is represented by an explicit policy object whose mode is `strict_preparation`. A future `rolling_preparation` policy must be a separate implementation and result-schema version.

`config/behaviour-calibration.json` contains every provisional human-behaviour coefficient, including the frustration sigmoid slope and phase-specific load/recovery coefficients. Simulation modules receive this calibration as data; coefficients are not hidden in the engines.

`config/parameter-registry.json` contains one record for every configurable leaf path in the default scenario and behaviour calibration. Each record has a path, value, status, source, note, and one display category: `calibrated`, `literature`, `user`, `operational`, or `provisional`. Registry validation fails when a configurable leaf lacks provenance or a record has an unknown status/category.

Scenario validation rejects unknown keys, missing required values after merge, invalid numeric ranges, incompatible aircraft geometry, unsupported policies, invalid access modes, invalid strategy/service-model identifiers, non-positive timing values, insufficient bus capacity, and invalid seeds. Errors are returned as stable path/code/message objects.

## Determinism contract

Every flight run and Monte Carlo batch requires an explicit integer seed. The package uses one fixed 32-bit PRNG algorithm with forked streams for population, preparation, access, aircraft, and conflict resolution. Simulation code must not use the Python `random` module, clock time, hash iteration order, or unordered tie-breaking.

Canonical serialization sorts dictionary keys, uses compact separators, rejects NaN/infinity, and uses the documented Python JSON floating-point representation. Tests compare serialized bytes for identical scenario/seed inputs and compare complete Monte Carlo output after excluding wall-clock metadata, which is not collected.

## Passenger and frustration state

Families remain graphs of individual passengers. Each passenger keeps their own seat, traits, state, events, latent load `X`, tolerance threshold `tau`, and frustration value:

`F = sigmoid((X - tau) / slope)`.

Tolerance is never multiplied into load growth. Each state integration updates:

- current latent load and frustration;
- initial frustration captured at T=0;
- peak frustration;
- cumulative frustration in F-minutes;
- seconds above the configurable frustration threshold.

The result reports passenger-level values and summary distributions. Behaviour coefficients are returned with a provisional model-status warning.

## Preparation policy and engine

`PreparationPolicy` defines the readiness decision without changing the meaning of timing metrics. `StrictPreparationPolicy` ends preparation only when both the overall readiness target and first-cohort readiness target are met. A scenario naming any unimplemented policy is rejected.

The preparation engine preserves the prototype's agent states and influences: waiting, standing, moving, correcting, staged, current frustration, urgency, social signal, family activity, visible progress, strategy complexity, compliance, trust, walking speed, and nonlinear crowd-density slowdown.

It records sampled progress plus correction events and returns a timeout status if the configured limit is reached.

## Bridge and bus access

Bridge access separately schedules boarding-control service, bridge walking, and minimum aircraft-door arrival spacing. It produces passenger arrival events and sampled access progress.

Bus access separately schedules allocation, parallel loading, capacity enforcement, dispatch, stochastic travel, front/rear unloading streams, and assigned-door arrivals. It never applies a constant bus penalty. Configuration is invalid when total bus capacity cannot carry the passenger population in the current single-trip reference policy.

Passenger frustration continues to evolve through access states. Progress history distinguishes waiting, in transit, arrived at door, entered aircraft, and seated counts.

## Aircraft cellular automaton

The A320 cabin has 30 rows, six seats per row, one aisle, explicit 0.4 m cells, and two aisle cells per row by default. Updates are synchronous at the configured interval.

At each update:

1. row services progress and completed passengers become seated;
2. current occupancy is snapshotted;
3. eligible walkers accumulate movement credit and propose only the adjacent cell toward their row;
4. occupied targets reject proposals;
5. multiple proposals for one free cell are resolved with the seeded aircraft RNG;
6. winning moves apply simultaneously;
7. the front and rear entry cells independently admit the next ready passenger when free.

A passenger at the target-row aisle cell blocks that cell until exactly one selected row-service model completes. The field model uses baggage Weibull draws and seat-interference movement counts. The user occupancy rule returns its complete 15/20/25/30/35-second service time and never adds baggage or seating time.

Audit events retain entry, movement, service start, and seating data. Invariant checks use these events to prove capacity, unique seating, adjacent movement, permitted direction, valid door flow, and the absence of simultaneous aisle/seat occupancy.

## Results and Monte Carlo

The top-level flight result includes schema/model versions, seed, normalized scenario, validation/model status, parameter provenance, passenger results, phase results, progress/frustration trajectories, summary metrics, timeout/invalid status, and deterministic diagnostics.

Phase metrics include preparation time, access time, embarkation time from preparation end to last seat, cabin time from first aircraft entry to last seat, and total T=0-to-last-seat time.

Passenger experience metrics include initial, burden, peak, and time-above-threshold distributions plus the share above the configured peak threshold.

Monte Carlo uses seeds `base_seed + run_index`, keeps input order, and reports requested, valid, timed-out, and invalid counts. Statistical summaries include minimum, P10, median, mean, P90, P95, maximum, and a deterministic 95% confidence interval for the mean. Failed/timed-out runs are excluded from numeric summaries but retained as status records. An empty valid set returns `null` summaries rather than infinities or fabricated zeros.

## Local UI

The visual thesis is a restrained operational workspace: warm neutral background, dark navy typography, one aviation-blue action accent, status colors used only for provenance and warnings, and no dashboard-card mosaic.

The content layout is:

- a compact scenario rail and run controls;
- a three-part horizontal process view with live counts and timings;
- T=0 passenger distribution;
- preparation progress with correction markers;
- bridge/bus and aircraft progress;
- mean and P90 frustration trajectory;
- timing and passenger-experience distributions;
- Monte Carlo strategy table with quantile/confidence ranges and invalid/timeout counts;
- parameter provenance table and calibration warning.

The interaction thesis uses a short results reveal after a run, animated progress-line drawing, and table-row emphasis when a strategy is selected. Motion is disabled for users requesting reduced motion. The interface is responsive and keyboard accessible, and every chart also has textual labels or a data table.

## Server and errors

`python -m boarding_sim` starts the local server and prints its URL. `GET /api/config` returns defaults, strategies, provenance, and model status. `POST /api/run` accepts `{scenario, seed}`. `POST /api/monte-carlo` accepts `{scenario, runs, baseSeed}`. Static requests serve only files inside `web/`.

Validation errors return HTTP 400 with structured issues. Simulation timeouts return HTTP 200 because they are modeled outcomes. Unexpected exceptions return a generic HTTP 500 body while full tracebacks remain on the local console.

## Verification and acceptance

Development follows red-green-refactor cycles. The suite covers deterministic bytes, population/seat uniqueness, family compatibility, strategy flow, readiness, bridge and bus events, service-model separation, synchronous occupancy, adjacency/no teleportation, allowed movement direction, unique seating, timeout handling, Monte Carlo determinism/counts/intervals, provenance coverage, and API/static-server behavior.

Acceptance requires:

- the complete Python test suite passes;
- every Python module compiles;
- no simulation module imports `random` or uses current time for seeds;
- parameter coverage validation passes;
- a deterministic baseline seats all 180 passengers;
- a bridge and a two-door bus scenario complete;
- a Monte Carlo smoke batch reports correct valid/timeout/invalid counts;
- the UI loads and successfully renders a real API result;
- documentation states the Layer 4 validation limitation clearly.

## Intentional scope limits

This implementation does not simulate arrival, check-in, security, terminal shopping, or other pre-T=0 processes. It does not add rolling preparation, multiple bus trips, non-A320 cabin layouts, operational calibration, a database, accounts, cloud hosting, or comparative operational recommendations.
