# Production Implementation Notes

## Authority and compatibility

The Python package was implemented against the handoff's normative documents and the preserved JavaScript prototype. The original `src/` code and `tests/simulation.test.mjs` remain in place as a reference; the local UI calls only the Python API.

The production implementation intentionally preserves:

- T=0 at the preparation announcement;
- strict preparation as its own policy;
- correlated passenger traits and individual family members;
- persistent latent load and a separate tolerance threshold;
- preparation decisions, crowding, corrections, and family effects;
- event-based bridge and bus access;
- synchronous adjacent movement through explicit 0.4 m aircraft cells;
- row-cell blocking during service;
- seeded conflict selection;
- separate field and user row-service models;
- independent front and rear aircraft streams;
- provisional labels for gate/frustration behavior.

## Deliberate production boundaries

The package rejects two-door strategies when bridge access is selected. The reference bridge process has one front-door stream; silently mapping a two-door method onto it would violate the model boundary.

The current bus policy supports one trip per configured bus. Scenario validation requires enough combined capacity for the passenger population. Multiple bus trips would need a separately documented dispatch policy.

The only supported aircraft is the 30-row, six-seat, 180-seat A320 reference geometry. Load factor may reduce the generated population, but cell geometry cannot be changed through an input patch.

Frustration trajectory samples use all passengers during preparation and passengers who are not yet seated during embarkation, matching the reference prototype's active-passenger interpretation.

## Calibration boundary

All provisional human-behaviour values live in `config/behaviour-calibration.json`. Engines receive this object as data. `config/parameter-registry.json` must match every scenario and behavior leaf by path and value; the test suite fails if values drift or provenance is missing.

The registry's five UI categories simplify longer evidence statuses:

- `calibrated`: field-calibrated or field-model-validated aircraft inputs;
- `literature`: published model settings/baselines without a new local calibration claim;
- `user`: explicit model, metric, or safety policy chosen by the product/user;
- `operational`: aircraft/airport/flight inputs supplied or to be supplied by an operator;
- `provisional`: parameters requiring local or passenger-behavior calibration.

## Determinism

The PRNG is a fixed 32-bit Mulberry32 implementation with deterministic distribution helpers and named fork offsets:

- population: 1;
- preparation: 2;
- access: 3;
- aircraft and conflict resolution: 4.

No simulation module imports Python's `random` package. Seeds never come from the clock. Boarding ranks use Fisher–Yates-derived random keys plus stable passenger IDs; dictionaries and events are serialized in stable order.

## Aircraft auditability

The aircraft result keeps entry, row-service, and seating events. The internal typed result also keeps every movement event with its prior cell, next cell, target cell, and door. Tests use this audit to prove adjacent-only movement and permitted direction.

Movement follows occupancy snapshots: a passenger cannot enter a cell occupied at proposal time, even if that cell will be vacated by another movement in the same update. Winning proposals then apply synchronously. Aircraft-door admission happens after movement updates and only when the appropriate entry cell is free.

## Web separation

`web/js/app.js` orchestrates the page; `race-canvas.js`, `results.js`, `expert.js`, and `share.js` each own one rendering concern. Browser code contains no randomness, frustration formula, baggage distribution, row-service calculation, movement rule, or strategy ordering rule. The Python package is the only production model implementation.

The UI uses semantic controls, a live table alternative to canvas, visible focus styles, reduced-motion event stepping, responsive layouts, and explicit unsuccessful Monte Carlo counts.

The tracked default artifact is compacted for delivery: research-only provenance/diagnostic duplicates are omitted, pre-preparation frustration frames reuse gate-frame values, and aircraft motion is visually interpolated between authoritative entry and seating events. Full `/api/compare` responses retain the complete audit replay.

## Known scientific limits

Passing the software-invariant suite satisfies only Layer 1 of `VALIDATION_PLAN.md`. It does not satisfy:

- Layer 2 reproduction of published aircraft reference scenarios;
- Layer 3 gate observation and calibration;
- Layer 4 passenger-response calibration and held-out validation.

No strategy ranking from the current default coefficients should be used as an operational recommendation.
