# Corrections applied from V1 to V2

1. Replaced independent random passenger properties with correlated latent-factor sampling.
2. Separated stable passenger traits from the changing passenger state.
3. Replaced direct random frustration with latent stress load plus an individual tolerance threshold.
4. Removed tolerance from the stress accumulation equation to avoid double-counting tolerance.
5. Added memory through persistent stress load and cumulative frustration burden.
6. Kept earlier airport experience outside the timeline and compressed it into T=0 state.
7. Replaced fixed per-method preparation time with agent decisions, movement, instruction comprehension, correction events, family effects and crowding.
8. Replaced hard-coded method-complexity scores with a structural complexity measure based on cohort count.
9. Added companion-compatible preparation/boarding ranks. Two-door half-cabin methods preserve seat-based door assignment to prevent artificial opposing aisle flows.
10. Replaced comparator-based random sorting with seeded Fisher–Yates shuffling.
11. Replaced `aisleFreeAt` with an explicit discrete aircraft aisle.
12. Aircraft aisle uses 0.4 m cells and synchronous movement proposals.
13. Added conflict resolution and explicit row blocking while baggage/seating service occurs.
14. Added field-derived Weibull baggage storage parameters: shape 1.7, scale 16 s.
15. Added seat-interference movement counts based on occupied seat positions.
16. Kept the user's 15 s / load-factor rule as a separate service model so it does not double-count field baggage/seating time.
17. Replaced “two doors = faster rate multiplier” with independent front and rear aircraft-door streams.
18. Replaced fixed bus penalty with explicit bus loading, capacity, travel and unloading events.
19. Replaced fixed bridge penalty with gate scan, bridge walk and aircraft-door headway events.
20. Added deterministic seeds and automated invariants/tests.
21. Added a parameter registry that separates field-calibrated, literature, user-defined, operational and provisional values.
22. Added Monte Carlo outputs as distributions rather than a single deterministic boarding time.
