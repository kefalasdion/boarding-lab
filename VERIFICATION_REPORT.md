# Verification Report

**Date:** 2026-08-14

**Model:** `pbs-v2-python-1.1.0`

**Result schema:** `1.1.0`

This report verifies software behavior and presentation quality. It does not establish scientific or operational validity.

## Automated suites

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
npm test
npm run test:e2e
bash tests/smoke_standalone.sh
python3 -m compileall -q boarding_sim scripts
node --check web/js/app.js
```

Fresh results:

- Python: **87 passed**, 0 failed;
- pure JavaScript/reference: **16 passed**, 0 failed;
- Playwright desktop/390 × 844 phone: **6 passed**, 0 failed;
- axe: **0 serious or critical violations** on desktop and phone;
- clean standalone smoke: passed using Python runtime only;
- Python and JavaScript syntax checks: passed.

Coverage includes fair manifest cloning, exact Strict Steffen ordering, deterministic gate coordinates, complete preparation, phase-specific timeouts, aircraft movement invariants, additive phase burdens, replay traceability, API limits/security headers, playback controls, sharing text, dynamic no-winner behavior, responsive overflow, and accessibility.

## Representative public comparison

The tracked artifact uses base seed `20260813`, 100 fair comparisons, and representative seed `20260841`.

| Strategy | Preparation finished | Boarding started | Boarding finished | Prep burden mean | Embarkation burden mean | Total burden mean |
|---|---:|---:|---:|---:|---:|---:|
| Random | 216.0 s | 252.0 s | 1229.0 s | 0.6264 F·min | 1.9985 F·min | 2.6249 F·min |
| Back-to-front | 195.0 s | 231.0 s | 1347.5 s | 0.6191 F·min | 2.5319 F·min | 3.1510 F·min |
| Strict Steffen | 231.0 s | 275.0 s | 960.0 s | 0.7155 F·min | 1.3162 F·min | 2.0317 F·min |

The three preparation finishes and three boarding starts are distinct. At intermediate clock positions, one method can still be preparing while another has moved to access or begun aircraft boarding. The clock never resets per lane.

The 100-run total-time P10/P50/P90 values are:

- Random: `1150.1 / 1256.25 / 1355.5 s`;
- Back-to-front: `1234.6 / 1340.5 / 1461.7 s`;
- Strict Steffen: `896.55 / 943.75 / 1011.15 s`.

These are model outputs under provisional preparation/frustration inputs, not an operational recommendation.

## Determinism and payload measurements

```bash
/usr/bin/time -p python3 scripts/build_default_comparison.py --workers 4
git diff --exit-code -- web/data/default-comparison.json
```

- 100-run artifact build: **125.06 s wall time**;
- regeneration diff: none;
- tracked default artifact: **3,850,741 bytes**;
- compact public `/api/compare` result at representative seed: **4,557,526 bytes**;
- live three-strategy comparison computation: **4.68 s**;
- compact per-strategy representative replays: about **1.16–1.29 MB** each;
- full internal results retain research diagnostics; public delivery omits those duplicates.

All simulation randomness comes from explicit seeded PRNG streams. No Python global-random import, browser randomness, or clock-derived seed is used.

## Playback performance

Command:

```bash
npm run measure:playback
```

Thirty-second Chromium run at 1440 × 900 with all 540 passenger marks active:

- sampled frames: **1,799**;
- median interval: **16.7 ms**;
- P95 interval: **17.6 ms**;
- maximum interval: **17.8 ms**;
- sustained stutter or unresponsive controls: none observed.

This meets the targets of median below 16.7 ms within timer precision and P95 below 33.3 ms.

## Browser and failure-state verification

Verified in a real desktop browser and at 390 × 844:

- scattered passengers form three visibly different queues;
- lane transitions follow their own preparation and first-entry timestamps;
- the live 0–100 frustration index remains separate from accumulated F·minutes;
- passenger inspector values come from serialized replay frames;
- preparation-finished, boarding-started, and boarding-finished values match the API;
- preparation, embarkation, and total burden are all visible and labeled “model-predicted” and “provisional”;
- timing table includes P10–P90, 95% mean intervals, and valid/timed-out/invalid counts;
- one-second preparation timeout produces no boarding events and no winner;
- canvas has a live text-table alternative;
- phone document width equals its 390 px viewport;
- keyboard-focusable scroll regions, visible focus, reduced-motion behavior, and contrast checks pass;
- no console/page errors occurred.

## Scientific acceptance status

- Layer 1 software invariants: implemented and passing.
- Layer 2 published reference-condition reproduction: still required.
- Layer 3 target-operation gate observation/calibration: still required.
- Layer 4 passenger frustration calibration and held-out validation: still required.

The UI therefore calls frustration `model-predicted` and `provisional`, attributes burden to time periods rather than claiming causation, and disallows operational claims.
