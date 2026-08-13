# Boarding Lab Public Experience Design

**Date:** 2026-08-13  
**Status:** Approved for implementation  
**Product:** Boarding Lab — By Dennis Kefalas  
**Inspiration:** Adam Jacobs's three-way A320neo boarding visualization

## Purpose

Turn the existing passenger-boarding research simulator into a polished public experience for a mixed audience of aviation professionals, researchers, students, and curious travelers.

The experience will revisit the three strategies shown in Adam Jacobs's viral visualization—Random, Back-to-front, and Strict Steffen—while exposing the cost that a boarding-only clock hides: passengers first have to be organized at the gate. It will also show each passenger's changing model-predicted frustration from the preparation announcement until seating.

The public question is:

> A smarter boarding order may fill the cabin faster, but is it still better after the time and passenger cost of preparing that order are included?

The application is a research experiment, not an operational recommendation. It may say that a method produced lower model-predicted frustration under the selected assumptions. It may not call that outcome scientifically proven passenger psychology.

## Product identity and audience

The visible identity is **Boarding Lab — By Dennis Kefalas**. Dennis's name is the trust signal; the experience is not presented as an Avioverse product.

The default journey must be understandable without aviation or simulation knowledge. Expert controls, sources, parameter provenance, distributions, and detailed results remain available after the visual comparison rather than dominating the first screen.

## Scientific and evidence boundary

The interface must keep three evidence categories distinct:

1. **Published or field-calibrated aircraft mechanics** — cabin cells, walking settings, luggage-storage distribution, seat interference, and selected aircraft-door inputs derived from the cited Schultz model lineage.
2. **Research-informed structure** — heterogeneous delay tolerance, information trust, family/group behavior, and evolving internal frustration state.
3. **Provisional human-behavior values** — the numerical coefficients governing preparation behavior, correction likelihood, and frustration accumulation. These remain model assumptions until fitted and validated against real gate observations and passenger responses.

Aircraft mechanics and software behavior may be described as literature-backed and tested. Gate-preparation and frustration results must be described as **model-predicted**. The methodology surface links every claim to `SOURCES.md`, `VALIDATION_PLAN.md`, and the parameter registry.

## Fair comparison contract

One seeded passenger manifest is created for each comparison and cloned into the three strategy runs. All runs therefore receive the same:

- 180 passengers and assigned seats;
- family and companion relationships;
- luggage counts;
- walking speeds and stable traits;
- tolerance thresholds and initial stress state;
- initial model-predicted frustration;
- randomized starting positions in the same gate geometry.

Only the boarding strategy and the preparation work caused by that strategy differ. Random streams that represent the same passenger property must be shared or deterministically paired so that strategy results are not confounded by different populations.

## Strategies in the public race

### Random

Passengers begin scattered throughout the gate and form a naturally ordered, first-come line. They do not have to sort themselves by seat or row. Families may stay together without changing the definition of the strategy.

### Back-to-front

The A320 cabin is divided into six five-row zones. Passengers move into the correct zone, while order within a zone remains flexible. Families remain compatible with the earliest applicable zone and any resulting override is reported.

### Strict Steffen

The public race uses the idealized theoretical method represented in the original visualization: window seats first, then middle, then aisle; alternating row parity and aircraft side; ordered back-to-front inside each subgroup. Every traveler has one exact queue slot.

Strict Steffen may separate companions because that is part of the theoretical method's real preparation cost. Separation events and affected passenger counts are reported. The interface labels the strategy **theoretical**.

The existing companion-compatible Steffen variant remains available in the expert workspace as **Practical Steffen**, but it is not substituted for Strict Steffen in the three-way public race.

## Gate preparation model

The gate is a bounded two-dimensional layout with a boarding-control point, waiting area, strategy-specific queue area, and collision-safe walking space.

At T=0, every passenger is placed at a unique seeded gate coordinate. Their assigned seat exists already, but nobody begins in a boarding line.

Preparation turns that scattered population into the line required by each strategy. The engine must explicitly produce:

- each passenger's starting coordinate;
- their required zone or exact queue slot;
- standing and movement decisions;
- collision-safe movement samples or path events;
- crowd slowdown;
- instruction misunderstanding and correction events;
- family or companion effects;
- time at which the passenger becomes correctly positioned;
- complete readiness state for the strategy.

The UI may interpolate between simulation samples for smoothness, but it may not invent destinations, corrections, queue order, or readiness.

All 180 passengers must be correctly prepared before a strategy begins boarding. This strict rule makes the hidden organization cost observable and keeps the preparation and embarkation phases unambiguous. If a preparation run reaches its safety limit, that strategy is reported as timed out and does not board.

## Continuous three-way race

The centerpiece is one continuous race under a shared clock that starts at the preparation announcement.

Each strategy advances independently:

1. passengers are scattered at the gate;
2. passengers form the strategy's required line;
3. the prepared line passes boarding control and the bridge;
4. passengers enter the aircraft, move through the aisle, stow luggage, resolve seat interference, and sit;
5. the strategy finishes when its final passenger is seated.

The clock never resets between preparation and boarding. Random can therefore be boarding while Strict Steffen is still organizing passengers. That visible overlap is the experience's central insight.

Desktop shows three synchronized horizontal lanes. Mobile stacks the lanes beneath a sticky master clock while keeping playback synchronized. The user can pause, replay, scrub, and select 0.5×, 1×, 2×, or 4× playback. Reduced-motion mode replaces continuous movement with discrete state changes and progress summaries.

## Passenger frustration visualization

Every passenger retains an individual model-predicted frustration value throughout preparation, transfer, cabin movement, and seating.

Passenger marks use a perceptually ordered scale:

- cool teal: calm;
- green: low;
- amber: rising;
- coral: elevated;
- magenta: high or severe.

The exact continuous value determines the color. A ring marks passengers at or above the configured `0.75` threshold so color is not the only signal. Reduced motion removes pulsing.

Hover, focus, or tap reveals:

- passenger and seat;
- current frustration value;
- current process state;
- peak frustration and accumulated burden so far;
- the active modeled stressors or recovery conditions;
- family or companion status when relevant.

After boarding, the aircraft becomes a selectable heatmap of peak frustration or total frustration burden. Accessible text and tables expose the same information without requiring color perception or pointer interaction.

## Result reveal

The result answers two separate questions:

1. Which method boarded the aircraft fastest after the first passenger entered?
2. Which method completed the full T=0-to-last-seat passenger journey best?

The primary ranking uses total time from preparation announcement to final seating. It does not assume a winner. A result headline is generated only from completed simulation data and states the observed trade-off in plain language.

Each strategy reports:

- preparation duration;
- access duration;
- cabin boarding duration;
- total T=0-to-last-seat duration;
- preparation corrections;
- family or companion separations/overrides;
- mean and P90 frustration burden;
- mean and P90 peak frustration;
- share of passengers whose peak exceeds `0.75`;
- valid, timed-out, and invalid run counts.

The visible animation is one representative deterministic run. The conclusion also uses a precomputed many-run comparison and displays median, P10–P90 typical range, mean confidence interval where applicable, and run counts. One lucky seed cannot decide the overall conclusion.

If a strategy times out or has no valid runs, completed strategies remain visible but the app does not declare an overall winner. Missing values render as unavailable, never as zero.

## Page structure

The public page follows this order:

1. compact brand line and evidence-aware premise;
2. immediate default comparison using the same three strategies;
3. continuous gate-to-aircraft race;
4. dynamic result reveal and passenger heatmap;
5. short explanation of why preparation changes the conclusion;
6. scenario controls for delay, prior gate wait, passenger mix, luggage, access mode, and seed;
7. expert workspace with all supported strategies, Monte Carlo detail, charts, provenance, and downloadable data;
8. methodology, sources, validation limits, credit to Adam Jacobs's inspiration, and Dennis's byline.

The page uses a warm neutral surface, dark navy typography, aviation blue for actions, and the passenger frustration scale only for passenger state. It avoids dashboard-card clutter. The live race is the dominant visual idea.

## Rendering and data boundaries

Python remains the single simulation authority. Browser code renders serialized results and may not reproduce strategy rules, frustration formulas, luggage distributions, movement rules, or readiness policy.

The Python result schema gains a compact comparison/replay structure containing:

- shared manifest identity and scenario;
- strategy-specific gate layout and queue assignments;
- time-stamped passenger state samples and discrete events;
- preparation readiness and boarding transition;
- existing access and aircraft events;
- per-passenger frustration values or compact reconstructable samples;
- summary and many-run comparison results.

The browser uses an HTML canvas for the 540 moving passenger marks and aircraft/gate visualization. Controls, explanations, methodology, result numbers, fallback tables, and all focusable interactions remain semantic HTML. Canvas hit testing maps pointer locations to passenger IDs; keyboard navigation uses an equivalent searchable passenger table and strategy summaries.

Rendering runs independently from simulation time. The renderer interpolates only between authoritative samples, clamps pixel ratio on dense devices, pauses when the page is hidden, and avoids allocating objects per frame.

## Errors and resilience

- Scenario validation issues appear beside the affected control and preserve the last successful result.
- A preparation or aircraft timeout is a modeled outcome, not a server failure.
- One failed strategy does not erase other completed results.
- Unexpected failures show a concise retry message and keep technical details out of the public page.
- Animation controls remain usable while replay data loads.
- The default comparison and many-run summary are generated during the build/finalization process so first visit does not require a long Monte Carlo wait.
- No result is cached or shared without its scenario, seed, model version, and evidence status.

## Sharing

The standalone finalization phase provides a deterministic result URL format, copyable summary text, and a downloadable social image generated from the completed result. The social asset includes the product name, Dennis's byline, the three total-time bars, the central preparation insight, and the model-predicted label.

The permanent public launch is deliberately deferred. After the standalone simulator is final, a separate project will integrate it into a FlyByCode article. The LinkedIn post will be published only after that FlyByCode page is live, so all traffic lands on the permanent article.

## Verification and acceptance

Existing software-invariant, aircraft, access, API, and UI-contract tests remain passing. New automated checks must prove:

- the three strategies receive identical cloned passengers and initial gate positions;
- gate coordinates and exact queue slots are unique and within bounds;
- passenger movement does not teleport or overlap at a simulation sample;
- Random, six-zone Back-to-front, and Strict Steffen assignments match their documented definitions;
- Strict Steffen separations are explicit and the practical variant retains companion compatibility;
- no strategy boards before all passengers are correctly prepared;
- time never resets at the phase transition;
- all UI movements, colors, counts, timings, and labels trace to serialized simulation output;
- identical scenario and seed produce byte-equivalent comparison/replay results;
- Monte Carlo summaries keep valid, timed-out, and invalid counts and uncertainty ranges;
- invalid and timeout states never fabricate winners or zero values;
- source, evidence-category, and provisional-model wording is present;
- keyboard, screen-reader, color-independent, reduced-motion, pause, replay, and speed controls work;
- the experience remains usable at common desktop and 390 × 844 mobile viewports;
- the live view sustains smooth playback with 540 visible passenger marks on the target machine;
- the complete Python suite, JavaScript tests, compile checks, and browser console check pass.

Acceptance also requires fresh visual inspection of a full default race and result at desktop and mobile sizes, including at least one high-frustration passenger inspection and a timed-out strategy state.

## Scope limits

This phase does not:

- claim validated passenger psychology or make operational recommendations;
- change the A320 180-seat reference aircraft;
- simulate arrival, check-in, security, shopping, or pre-T=0 terminal behavior;
- add accounts, a database, comments, analytics, or paid features;
- integrate into or modify the FlyByCode repository;
- deploy a permanent public URL;
- publish the LinkedIn post.

FlyByCode integration, production deployment, article composition, analytics, final social asset capture, and LinkedIn publication form a later approved phase after this standalone experience is complete.
