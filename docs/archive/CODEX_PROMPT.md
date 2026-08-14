# Codex implementation brief

Implement the Passenger Boarding System Simulator from this handoff as a production-quality simulation module and UI.

## Non-negotiable model boundary

T=0 = announcement to prepare for boarding.

Do not simulate airport arrival/check-in/security. Earlier experience enters only as initial-condition inputs.

The product must preserve these three conceptual parts:

1. passenger state at T=0;
2. preparation required by the boarding method;
3. embarkation through bridge/bus and aircraft until the final passenger is seated.

## Source of truth

Read before changing code:

1. `MODEL_SPEC.md`;
2. `config/parameter-registry.json`;
3. `VALIDATION_PLAN.md`;
4. `CHANGELOG_V1_TO_V2.md`;
5. `SOURCES.md`.

The code in `src/` is the executable reference prototype. Preserve the model semantics unless a change is documented and tested.

## Architecture

Create a simulation package with pure deterministic modules:

- scenario/config validation;
- seeded PRNG;
- population generator;
- boarding-strategy policy;
- preparation engine;
- bridge/bus access engine;
- aircraft CA engine;
- passenger state/frustration engine;
- Monte Carlo runner;
- metrics and result schema.

Keep rendering/UI separate from simulation.

## Rules

- Never use `Math.random()` in simulation code;
- every run accepts an explicit seed;
- same seed + same scenario = byte-equivalent numeric result, subject only to documented floating-point serialization;
- every parameter must have provenance/status;
- do not mix `USER_DEFINED` row-service logic with field baggage/seat-shuffle timing;
- do not replace the aircraft CA with a global aisle timer;
- do not model two aircraft doors as a scalar speed multiplier;
- do not model bus access as a constant penalty;
- do not collapse families into one passenger;
- do not label the frustration output "validated" until Layer 4 in `VALIDATION_PLAN.md` passes;
- show uncertainty intervals in Monte Carlo comparisons;
- surface timed-out/invalid run counts.

## Aircraft CA requirements

Use explicit 0.4 m cells and synchronous updates.

Each passenger:

- enters through assigned aircraft door;
- advances only when the next cell is available;
- blocks the target-row aisle cell during row service;
- uses either the field service model or the user occupancy rule;
- becomes seated only after service completion.

Implement conflict resolution deterministically using the seeded RNG.

## Passenger-state requirements

Maintain latent stress load `X_i(t)` and tolerance threshold `tau_i` separately.

`F_i(t) = sigmoid((X_i(t)-tau_i)/s)`.

Do not multiply stress growth by tolerance again.

Track:

- initial F;
- peak F;
- cumulative F·minutes;
- time above configurable threshold;
- distribution across passengers.

All behaviour coefficients are provisional and must live in a calibration/config layer.

## Preparation requirements

V2 reference mode is strict-preparation mode to preserve clean three-part timing.

Implement readiness as an explicit policy object so a later `rolling_preparation` mode can be added without changing metric definitions silently.

## Tests

Port and expand `tests/simulation.test.mjs`.

Add property/invariant tests for:

- occupancy;
- unique seating;
- no teleportation;
- no backwards movement except explicitly allowed policies;
- front/rear split flow;
- family compatibility;
- service-model separation;
- deterministic Monte Carlo;
- timeout handling;
- parameter schema/provenance.

## UI

The UI should show:

- Part 1 passenger-state distribution at T=0;
- Part 2 preparation progress and correction events;
- Part 3 bridge/bus and aircraft boarding progress;
- mean and P90 frustration trajectory;
- total T=0-to-last-seat time;
- prep time;
- embarkation time;
- cabin boarding time;
- frustration burden distribution;
- peak-frustration distribution;
- Monte Carlo confidence/quantile ranges;
- parameter provenance badges: calibrated / literature / user / operational / provisional.

## Deliverable

Do not merely restyle the prototype. Build the simulator as a reusable engine with tests, typed result schemas, parameter provenance and a calibration-ready boundary.
