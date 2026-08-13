# Normative Model Specification

## 1. Simulation boundary

**T=0 is the airline announcement to prepare for boarding.**

The simulation does not model terminal arrival, check-in, security, shopping or the full airport journey. Their effects may enter only through scenario inputs used to generate passenger state at T=0.

## 2. Passenger representation

Each passenger `i` has:

### Stable traits for one simulation run

- tolerance threshold `tau_i`;
- delay sensitivity;
- uncertainty sensitivity;
- waiting sensitivity;
- crowd sensitivity;
- social susceptibility;
- compliance;
- trust in information;
- walking speed;
- family/group relation;
- hand luggage count;
- seat and row.

These are generated from shared latent factors so they are correlated rather than sampled independently.

### Dynamic state

- stress load `X_i(t)`;
- frustration `F_i(t)`;
- cumulative frustration burden;
- peak frustration;
- location/process state;
- preparation state;
- aircraft state.

## 3. Frustration mapping

Tolerance is a threshold, not another multiplier in stress growth.

```text
F_i(t) = sigmoid((X_i(t) - tau_i) / s)
```

`X_i(t)` carries memory. It increases under stressors and decreases under recovery conditions.

```text
dX_i/dt = stressors_i(t) - recovery_i(t)
```

The cumulative passenger-experience metric is:

```text
B_i = integral(F_i(t) dt)
```

The flight-level result must report the distribution of `B_i`, not only its mean.

### Status

The structure is intentional. The human-behaviour coefficients are provisional until calibrated against normal passenger observations and surveys.

## 4. T=0 initial condition

Earlier airport experience is compressed into `X_i(0)` using:

- current flight delay;
- previous delay updates;
- prior gate waiting input;
- prior airport dwell input;
- fatigue;
- connection pressure;
- delay sensitivity;
- uncertainty sensitivity;
- information trust.

The code must never sample `F_i(0)` independently of these variables.

## 5. Families/groups

A family is a graph relation between individual agents, not a single super-agent.

Default rules:

- each member retains individual traits and frustration;
- group members are kept in a compatible preparation cohort;
- their boarding ranks remain contiguous;
- for two-door half-cabin methods, seat-based aircraft-door assignment is preserved to prevent artificial opposing aisle traffic;
- any future alternative family policy must be explicit and configurable.

## 6. Preparation phase

Preparation is not a fixed strategy penalty.

At each preparation step passengers may:

- remain seated/waiting;
- stand;
- begin moving toward the staging/queue area;
- arrive at staging;
- misunderstand the instruction;
- undergo a correction event;
- become correctly staged.

Decision probability depends on:

- current frustration;
- urgency;
- social signal from other passengers;
- family activity;
- visible progress;
- method structural complexity;
- compliance.

Movement time depends on passenger walking speed and a nonlinear gate-density slowdown.

Instruction comprehension depends on compliance, trust and method structural complexity.

### Readiness

V2 uses a **strict preparation experiment** to preserve the user's three-part boundary. `readinessTarget` and `firstCohortTarget` are explicit operational policy inputs.

A future production mode should support rolling preparation during embarkation. Codex must not silently merge that future behaviour into this mode because the metric definition changes.

## 7. Boarding strategies

Implemented:

1. random, front door;
2. rows 1–15 front / rows 16–30 rear;
3. A/F, then B/E, then C/D;
4. back-to-front, 5-row zones;
5. outside-in plus back-to-front zones;
6. Steffen-style, companion compatible;
7. split doors plus outside-in.

Strategy code produces:

- preparation cohort;
- boarding rank;
- assigned aircraft door.

No strategy may alter the physical aircraft model.

## 8. Bridge access

The bridge access model contains separate events:

1. boarding-control service;
2. bridge walking;
3. aircraft-door arrival spacing.

Bridge geometry and gate-scan service are operational inputs. The baseline aircraft-door spacing is a literature baseline and must remain configurable.

## 9. Bus access

Bus access is event-based, not a fixed time penalty.

The model contains:

1. bus allocation;
2. bus loading;
3. capacity limit;
4. dispatch;
5. stochastic travel time;
6. front/rear unloading streams;
7. arrival at the assigned aircraft door.

Bus timing parameters require local operational calibration.

## 10. Aircraft cellular automaton

### Geometry

- A320, 30 rows, 6 seats per row;
- one aisle;
- 0.4 m cell length;
- two aisle cells per row in this implementation;
- one passenger maximum per aisle cell.

### Time

Default update interval is 0.5 s.

### Movement

At every step:

1. snapshot aisle occupancy;
2. walking passengers propose movement toward their target row;
3. occupied target cells block movement;
4. simultaneous proposals to one cell are resolved with the seeded PRNG;
5. front and rear streams are independent;
6. a passenger reaching their row occupies and blocks the aisle cell while row service is completed;
7. the passenger then becomes seated and frees the aisle cell.

There is no global aisle-blocking timer.

## 11. Row service models

### A. Field-calibrated/literature model

Hand luggage storage uses a Weibull distribution:

```text
shape = 1.7
scale = 16.0 s
```

Seat interference uses movement counts based on occupied seats in the target side of the row.

The worst window-seat case with both middle and aisle already occupied uses nine movements.

### B. User occupancy rule

Alternative model:

```text
load < 60%       -> 15 s
60% to <70%      -> 20 s
70% to <80%      -> 25 s
80% to <90%      -> 30 s
90%+              -> 35 s
```

This is a complete alternative row-service model. Do not add field baggage/seating time on top of it.

## 12. Monte Carlo

A simulation result is a distribution across population seeds.

At minimum report:

- preparation time distribution;
- embarkation time distribution;
- cabin boarding time distribution;
- total T=0-to-last-seated time distribution;
- mean and P90 frustration burden;
- mean and P90 peak frustration;
- share of passengers with peak frustration >0.75;
- correction-event distribution;
- timeout/failure rate.

## 13. Reproducibility

All randomness must come from the seeded PRNG.

Forbidden in the simulation core:

- `Math.random()`;
- current-clock seeds;
- unstable random comparator sorts;
- hidden UI-only parameters.

Given the same scenario and seed, the engine must return identical results.
