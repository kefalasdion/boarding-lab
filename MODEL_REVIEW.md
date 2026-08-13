# Model Consistency Review — V2

## Overall conclusion

The V2 architecture is internally consistent for implementation and Monte Carlo experimentation.

It is **not yet a validated passenger-frustration predictor**. The aircraft boarding layer has published calibration support; the gate/frustration layer requires new data.

## Status matrix

| Model element | V2 status | Decision |
|---|---|---|
| Simulation starts at gate preparation announcement | Consistent | Keep |
| Earlier airport history compressed into T=0 state | Consistent | Keep |
| Monte Carlo passenger population | Consistent | Keep |
| Correlated passenger traits | Corrected | Replaced independent sampling |
| Families as linked individuals | Corrected | Keep individual agents |
| Dynamic frustration with memory | Corrected | Latent load + tolerance threshold |
| Tolerance heterogeneity | Corrected | Threshold only; no double count |
| Delay/trust/uncertainty influence | Structurally supported | Coefficients require calibration |
| Social frustration coupling | Structurally plausible | Provisional coefficient only |
| Fixed preparation penalty by method | Rejected | Replaced with agent preparation simulation |
| Method complexity | Corrected | Derived from cohort structure; human coefficient remains provisional |
| Readiness | Explicit policy | Strict V2 mode; rolling mode is a separate future model |
| Bridge fixed penalty | Rejected | Event-based scan/walk/headway |
| Bus fixed penalty | Rejected | Capacity/load/travel/unload process |
| Global aircraft aisle timer | Rejected | Explicit discrete aisle CA |
| One passenger per aisle cell | Supported | Implemented |
| 0.4 m cell size | Published model basis | Implemented |
| 0.8 m/s aisle speed | Published model setting | Implemented as cabin cap |
| Baggage storage Weibull 1.7 / 16 s | Field calibrated | Implemented |
| Seat interference | Published model basis | Implemented by occupied-seat pattern |
| Two doors as scalar multiplier | Rejected | Independent streams implemented |
| User 15 s / +5 s load rule | User-defined | Preserved as separate service model |
| Random comparator sorting | Rejected | Seeded Fisher–Yates |
| Reproducibility | Required | Seeded deterministic core |
| Operational ranking before human-factor calibration | Not permitted | UI warns user |

## Known limitations that are intentionally not hidden

1. Gate preparation does not yet use measured gate geometry from a specific airport.
2. Gate scan, bridge geometry and bus service distributions are placeholders until local data are supplied.
3. Passenger frustration coefficients are provisional.
4. Social coupling is a low-strength modelling mechanism, not a calibrated contagion model.
5. V2 uses strict preparation to maintain a clean three-part experiment. A rolling-preparation model must be implemented as a separate policy because it changes timing and feedback.
6. The two-door family rule keeps preparation cohorts together but preserves seat-based door assignment for half-cabin methods. This avoids impossible opposing aisle flows.
7. No claim is made that the current default strategy ranking matches a specific airline or airport.
