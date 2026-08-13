# Verification Report

**Date:** 2026-08-13  
**Model:** `pbs-v2-python-1.0.0`  
**Result schema:** `1.0.0`

## Automated Python suite

Command:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Final result: **66 tests passed, 0 failed**.

Coverage includes:

- fixed PRNG and canonical bytes;
- strict scenario validation and provenance coverage/value matching;
- individual passengers, unique seats, correlated traits, and family compatibility;
- separate latent load/tolerance and all required frustration metrics;
- explicit strict-preparation policy, progress, corrections, and timeout;
- bridge scan/walk/headway events;
- bus capacity/loading/dispatch/travel/front-rear unloading events;
- aircraft cell occupancy, adjacent movement, permitted direction, and unique seating;
- independent door streams and seeded conflict resolution;
- field/user service separation and exact custom-rule thresholds;
- deterministic complete flight and Monte Carlo results;
- valid/timeout/invalid Monte Carlo aggregation and uncertainty intervals;
- API validation/timeout/static-path behavior;
- required UI surfaces, provenance badges, accessibility, and rendering separation.

## Preserved JavaScript reference suite

Command:

```bash
npm test
```

Result: **5 tests passed, 0 failed**.

## Static checks

The following succeeded:

```bash
python3 -m compileall -q boarding_sim
node --check web/app.js
```

The final verification also scans production simulation sources for forbidden `random` imports, clock-derived seeds, and `Math.random`.

## Deterministic smoke scenarios

Seed `20260813`, default bridge scenario:

- status: `valid`;
- seated: `180/180`;
- preparation: `126.0 s`;
- last aircraft-door arrival relative to preparation end: `694.9931886778905 s`;
- embarkation: `1091.5 s`;
- cabin boarding: `1058.5 s`;
- T=0 to last seat: `1217.5 s`.

Seed `20260813`, bus access with `split_half_two_door`:

- status: `valid`;
- seated: `180/180`;
- preparation: `135.0 s`;
- last aircraft-door arrival relative to preparation end: `383.00174307797283 s`;
- embarkation: `927.5 s`;
- cabin boarding: `626.5 s`;
- T=0 to last seat: `1062.5 s`.

Serializing the default result twice produced identical **461,775-byte** canonical JSON outputs.

A three-run default Monte Carlo batch using seeds `91000`–`91002` reported:

- requested: 3;
- valid: 3;
- timed out: 0;
- invalid: 0;
- total-time P10/P50/P90: `1155.5 / 1169.5 / 1195.9 s`;
- total-time 95% mean interval: `1145.6484417420133–1203.6848915913201 s`.

## Browser verification

The local application was inspected in a real browser at desktop and 390 × 844 mobile viewports.

Verified:

- default bridge run rendered `180/180` seated;
- selecting the half-cabin two-door method automatically selected bus access;
- the two-door result rendered two buses and `180/180` seated;
- all seven strategies completed a two-run browser comparison: 14 valid, 0 timed out, 0 invalid;
- timing, preparation, embarkation, frustration, burden, peak, uncertainty, and provenance surfaces rendered;
- no browser console errors occurred;
- controls and primary results remained visible on the mobile breakpoint.

## Scientific acceptance status

This report verifies software behavior, not scientific or operational validity.

- Validation Layer 1: implemented automated invariant coverage.
- Validation Layer 2: published reference-condition reproduction remains future validation work.
- Validation Layer 3: target-operation gate observation/calibration remains future work.
- Validation Layer 4: passenger frustration calibration/held-out validation remains future work.

The UI and result schema therefore keep frustration labeled provisional and do not authorize operational strategy claims.
