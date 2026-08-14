# Validation Plan

The model must pass four separate validation layers. Do not call the whole model "validated" because one layer matches field data.

## Layer 1 — software invariants

Required automated tests:

- deterministic output for identical seed and scenario;
- 180 unique passengers and 180 unique seats;
- at most one passenger per aisle cell;
- no passenger can be seated twice;
- all aircraft-door assignments are valid;
- front/rear split strategies use both streams;
- same passenger cannot occupy aisle and seat simultaneously;
- service timers cannot become negative before completion logic;
- custom 15 s rule transitions exactly at 60%, 70%, 80%, 90%;
- Monte Carlo aggregation excludes failed/timed-out runs and reports their count.
- all public strategies clone one strategy-neutral passenger manifest;
- each public lane begins access no earlier than its own preparation finish;
- a preparation timeout creates no access or aircraft events and no winner;
- preparation burden plus embarkation burden equals total burden;
- replay starts at T=0, traces every passenger, and remains deterministic.

## Layer 2 — aircraft boarding model validation

Reproduce published reference conditions before tuning the new gate/frustration layers.

Compare:

- boarding-time distribution;
- aircraft-door arrival rate;
- aisle walking speed;
- baggage storage distribution;
- seat-shuffle durations;
- random boarding baseline;
- at least one published structured boarding trial.

Target for the implemented reference conditions: match published/field validation within the same order as the source study. The Schultz field-validation paper reported small differences for its tested validation scenarios. Do not transfer that error claim to new scenarios without reproducing the conditions.

## Layer 3 — gate preparation validation

Collect real gate observations.

Minimum event timestamps per passenger or anonymized trajectory sample:

- preparation announcement;
- stand-up time;
- first movement toward gate;
- queue/staging arrival;
- correction/misrouting event;
- boarding-control passage;
- family/group identifier;
- boarding group/cohort;
- gate density snapshots.

Fit the preparation decision and correction parameters to these observations.

Validate on flights not used for fitting.

## Layer 4 — frustration model validation

The current human-behaviour coefficients are provisional.

Collect short repeated passenger ratings, for example at:

1. immediately before preparation announcement;
2. after preparation/queue formation;
3. after boarding-control passage or bus loading;
4. after seating.

Capture explanatory variables:

- actual delay;
- perceived expected additional wait;
- trust in information;
- crowding perception;
- family/group travel;
- connection pressure;
- perceived fairness;
- perceived progress;
- fatigue proxy.

Fit the latent-load coefficients and tolerance distribution with hierarchical estimation.

Validate calibration and discrimination on held-out flights.

## Sensitivity and identifiability

Before fitting, run global sensitivity analysis on provisional behaviour parameters.

Do not fit several coefficients that produce indistinguishable outputs. Fix or remove non-identifiable parameters.

## Acceptance rule for operational use

The application may be used for operational claims only after:

- software invariants pass;
- aircraft reference scenarios reproduce accepted results;
- gate preparation parameters are calibrated to the target airport/airline environment;
- frustration predictions are validated against passenger responses;
- uncertainty intervals are displayed for every comparative result.
