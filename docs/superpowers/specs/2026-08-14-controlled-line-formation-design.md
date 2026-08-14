# Controlled line-formation model

## Purpose

Replace the unrealistic assumption that all passengers can simultaneously organize themselves into preassigned gate positions. Model the approved scenario in which each strategy forms its complete line before aircraft access begins.

## Preparation control

Preparation has two distinct actions: a passenger becomes eligible to move after the appropriate call, then the existing passenger model governs response, walking, crowding, mistakes, correction, and final staging.

The provisional release rules are:

- **Random:** one general announcement at T=0 makes every passenger eligible. Passengers form an ordinary random line; no seat or zone sorting is requested.
- **Back-to-front:** the six zones are announced from the rear forward at 20-second intervals. Every passenger in an announced zone becomes eligible together.
- **Strict Steffen:** passengers are called individually in exact Steffen order at four-second intervals. A passenger cannot begin forming the line before being called.

All three strategies retain the `complete_preparation` readiness rule: aircraft access starts only after every passenger has reached the strategy's complete line. The final Strict Steffen call therefore cannot occur earlier than 11:56 after T=0 for 180 passengers; response, movement, corrections, and family effects extend preparation beyond that lower bound.

## Events and outputs

- Record `preparation_general_call`, `preparation_zone_called`, or `preparation_passenger_called` events at their modeled times.
- Keep `preparation_started` as the moment a passenger responds and begins moving.
- Preparation-finished, boarding-started, and boarding-finished outputs remain on the same master clock.
- Family-separation stress remains active for Strict Steffen and continues to affect live and accumulated frustration.
- All release intervals are named, provisional calibration values with parameter-registry provenance.

## Model boundaries

This change introduces the missing operational call bottleneck. It does not claim that four seconds is an observed universal gate-agent rate. It does not simulate public-address intelligibility, multiple gate agents, absent passengers, boarding-pass verification during line formation, or detailed collision-avoidance paths. Those require operational observations.

The existing random-line and zone movement models remain provisional. The video must describe the output as a transparent scenario assumption rather than a measured airport result.

## Verification

- Test first that uncalled Strict Steffen passengers cannot start moving.
- Verify call events occur in exact boarding order at four-second intervals.
- Verify back-to-front zones are released at 20-second intervals and Random receives one general call.
- Verify Strict Steffen preparation cannot finish before its final passenger call.
- Rebuild the 100-run comparison and regenerate the LinkedIn video.
- The video must visibly distinguish the long line-formation period and retain separate speed and modeled-frustration conclusions.
