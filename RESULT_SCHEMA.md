# Public Result Schema

The Python API returns typed dataclasses from `boarding_sim.models`. The JSON API and canonical serializer convert their field names directly to JSON. Result keys use `snake_case`; `/api/config` uses a small UI-facing `camelCase` envelope.

## Flight result

`run_flight(scenario_patch, seed)` returns:

| Field | Meaning |
|---|---|
| `schema_version` | Version of this public data layout. |
| `model_version` | Version of the implemented model semantics. |
| `seed` | Explicit 32-bit run seed. |
| `status` | `valid` or `timed_out`. Validation errors are raised before a flight result exists. |
| `model_status` | Evidence limits and the Layer 4 warning. |
| `scenario` | Complete normalized scenario after strict default merging. |
| `strategy` | Selected policy identity, cohort count, and recommended access mode. |
| `parameter_provenance` | Complete provenance registry used for the run. |
| `passengers` | Individual final passenger records, including T=0 fields and experience metrics. |
| `phases` | The three conceptual model parts described below. |
| `replay` | Compact authoritative gate frames, frustration frames, aircraft events, codebooks, and passenger tracks. |
| `trajectory` | Chronological mean/P90 frustration and progress samples. |
| `metrics` | Timing, passenger-experience, readiness, and run-status summaries. |
| `diagnostics` | Deterministic stream and audit information that does not change metric definitions. |

## The three parts

### `phases.part1_t0_state`

Always has `time_seconds: 0`. It contains passenger count and distributions for initial frustration, tolerance threshold, and initial latent stress load. Earlier airport experience is not represented as events.

### `phases.part2_preparation`

Contains the explicit policy, duration, timeout state, final readiness, strategy complexity, correction count, progress samples, and preparation events.

The expert default is `strict_preparation`. The public comparison uses `complete_preparation`, which requires every passenger to reach their strategy-defined slot. A preparation timeout leaves embarkation `status: "not_started"`, with empty access/aircraft events and null unobserved timings.

### `phases.part3_embarkation`

Contains:

- `access`: bridge or bus events, progress, bus summaries where applicable, and final aircraft-door arrival time;
- `aircraft`: first entry, last seat, cabin duration, progress, aircraft events, timeout, and CA diagnostics.

`duration_seconds` runs from preparation end to the observed final seat. It is `null` after an aircraft timeout.

## Timing definitions

All timing values use seconds from T=0 unless their key says `duration`.

| Metric | Definition |
|---|---|
| `preparation` | T=0 to strict readiness or preparation timeout. |
| `access_until_last_door_arrival` | Preparation end to the final passenger's aircraft-door arrival. |
| `embarkation` | Preparation end to final seating. `null` if final seating is not observed. |
| `cabin_boarding` | First aircraft entry to final seating. `null` if either point is not observed. |
| `total_t0_to_last_seat` | T=0 to final seating. `null` after timeout. |

Access and cabin time overlap: passengers can enter the aircraft while later passengers remain on the bridge or bus process. Therefore access time plus cabin time is not expected to equal embarkation time.

## Distribution summary

Every non-empty numeric distribution contains:

- `count`;
- `minimum` and `maximum`;
- `p10`, `p50`, `p90`, and `p95` using linear interpolation;
- arithmetic `mean`;
- `mean_ci95_low` and `mean_ci95_high`, calculated as mean ± 1.96 standard errors.

An empty Monte Carlo valid set returns `null` summaries. It never returns infinity, NaN, or invented zero values.

## Passenger experience

`metrics.passenger_experience` contains distributions across individual passengers for:

- `initial_frustration`;
- `frustration_burden_f_minutes`;
- `peak_frustration`;
- `time_above_threshold_minutes`.

It also reports the configured `threshold` and `share_peak_above_threshold`.

Passenger frustration is provisional:

```text
F_i(t) = sigmoid((X_i(t) - tau_i) / slope)
```

`X_i` and `tau_i` remain separate. Tolerance is not multiplied into stress growth.

The burden fields are:

- `preparation_frustration_burden_f_minutes`;
- `embarkation_frustration_burden_f_minutes`;
- `total_frustration_burden_f_minutes`;
- legacy alias `frustration_burden_f_minutes`, equal to total.

For every passenger and distribution mean, preparation burden plus embarkation burden equals total burden within floating-point tolerance. These are time attributions (“accumulated during”), not causal claims (“caused by”).

## Fair comparison result

`run_comparison(scenario_patch, seed)` returns fixed `strategy_order` values `random_front`, `back_to_front_zones`, and `strict_steffen`. All three contain the same `manifest_fingerprint`. `winner` and the server-provided ordering are present only when all strategies are valid.

`run_comparison_monte_carlo` adds per-strategy timing, burden, correction, and companion-separation summaries, win counts, and valid/timed-out/invalid run counts. Its public API cap is 200 runs.

## Replay contract

`replay` begins at T=0 and ends at the observed final seat or preparation timeout. `gate.frames` serialize time, live mean frustration, mean accumulated burden, and per-passenger position/state. `frustration_frames` continue the same two live aggregates through embarkation. `aircraft_events` use `event_codebook`; browser code may interpolate between frames but may not recalculate states, frustration, timings, or the winner.

## Monte Carlo result

`run_monte_carlo(scenario_patch, runs, base_seed)` uses seed `base_seed + run_index` and returns:

- schema/model versions and normalized scenario;
- `requested_runs`, `valid_runs`, `timed_out_runs`, and `invalid_runs`;
- metric `summaries` calculated from valid runs only;
- ordered `run_records` containing each seed and status.

Timed-out and invalid records remain visible but never enter the numeric distributions.

## Canonical JSON

`canonical_json_bytes` uses UTF-8, sorted dictionary keys, compact separators, JSON booleans/null, `ensure_ascii=False`, and `allow_nan=False`. Floating-point values use the Python runtime's JSON number serialization. Identical model version, scenario, seed, Python version, and supported platform produce byte-equivalent output.
