# Verification Report

**Date:** 2026-08-24

**Model:** `pbs-v2-python-1.2.0`

**Result schema:** `1.1.0`

This report verifies software behavior and presentation quality. It does not establish scientific or operational validity.

## Automated suites

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
npm test
npm run test:e2e
```

Fresh results:

- Python: **115 passed**, 0 failed;
- browser modules and pure JavaScript reference: **22 passed**, 0 failed;
- Playwright desktop and 390 × 844 phone: **6 passed**, 0 failed.

The standalone smoke script, the `compileall` and `node --check` syntax passes, and the axe run outside the Playwright suite were **not re-measured** for this model version.

Coverage includes fair manifest cloning, exact Strict Steffen ordering, deterministic gate coordinates, complete preparation, gate reachability for every floor slot, phase-specific timeouts, aircraft movement invariants, additive phase burdens, replay traceability, API limits/security headers, playback controls, sharing text, dynamic no-winner behavior, responsive overflow, and accessibility.

New in this model version: `tests/test_gate_reachability.py` covers the gate-movement fix, asserting that previously stalling seeds now complete, that every passenger is correctly staged before boarding, and that `companion_separations` is distinct from `companion_overrides`.

## Representative public comparison

**No results table is published in this report.** The tracked 100-run artifact has been rebuilt for `pbs-v2-python-1.2.0`, and all 100 comparisons completed. The previous table and the previous total-time P10/P50/P90 block described model `1.1.0`, before the gate-movement fix, and have been deleted rather than restated, because carrying them forward would misreport the current model.

The authority for representative and distribution figures is the tracked artifact itself, [`web/data/default-comparison.json`](web/data/default-comparison.json), rebuilt with:

```bash
python3 -m scripts.build_default_comparison --workers 4
```

The structural properties the suites assert about that artifact still hold: the three preparation finishes and three boarding starts are distinct, at intermediate clock positions one method can still be preparing while another has moved to access or begun aircraft boarding, and the clock never resets per lane.

Every figure produced from that artifact is a model output under provisional preparation and frustration inputs, not an operational recommendation.

## Determinism and payload measurements

All simulation randomness comes from explicit seeded PRNG streams. No Python global-random import, browser randomness, or clock-derived seed is used. Determinism for identical seed and scenario is asserted by the passing Python suite.

Artifact build wall time, tracked artifact size, compact `/api/compare` payload size, live comparison computation time, and per-strategy replay sizes were **not re-measured** for this model version. The previous figures have been removed rather than carried forward.

## Playback performance

Command:

```bash
npm run measure:playback
```

This measurement was **not re-run** for this model version, so no frame-interval figures are reported here. The previously stated targets are unchanged: median interval below 16.7 ms within timer precision, and P95 below 33.3 ms.

## Browser and failure-state verification

Verified by the passing Playwright suite in Chromium at desktop size and at 390 × 844:

- the default comparison loads and reports either a winner or an explicit no-winner headline;
- the timing table shows preparation finished, boarding started, boarding finished, and frustration accumulated during preparation;
- the three lanes have distinct preparation finishes and distinct first aircraft entries, and at a staggered clock position each lane reports its own phase;
- a one-second preparation timeout produces no winner, no aircraft events, and a `not_started` embarkation phase in every strategy;
- phone document scroll width equals its client width, so there is no document-level horizontal overflow;
- axe reports **0 serious or critical violations** on the loaded page;
- no console or page errors occurred.

The wider manual browser walkthrough recorded in earlier versions of this report — passenger inspector values, reduced-motion behaviour, contrast checks, keyboard-focusable scroll regions and the canvas text-table alternative — was **not repeated** for this model version.

## Scientific acceptance status

- Layer 1 software invariants: implemented and passing.
- Layer 2 published reference-condition reproduction: still required.
- Layer 3 target-operation gate observation/calibration: still required.
- Layer 4 passenger frustration calibration and held-out validation: still required.

The UI therefore calls frustration `model-predicted` and `provisional`, attributes burden to time periods rather than claiming causation, and disallows operational claims.
