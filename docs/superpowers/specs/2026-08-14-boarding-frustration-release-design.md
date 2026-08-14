# Boarding frustration release design

**Date:** 2026-08-14
**Status:** Approved for implementation
**Branch:** `feature/boarding-frustration-release`
**Product:** Boarding Lab — By Dennis Kefalas

## Purpose

Produce the three public deliverables for the passenger-frustration story:

1. a LinkedIn video that shows the experiment running, with no narration and no explainer cards;
2. a research collection covering the papers, methods and real-world observations behind the experiment;
3. a repository prepared for open-source publication.

The written argument lives in the LinkedIn post copy, not in the video. The video's only job is to
show the experiment honestly.

A model correction comes first, because the current results are produced by an assumption the author
has already rejected in writing.

## Ordering constraint

`docs/superpowers/specs/2026-08-14-controlled-line-formation-design.md` is specified but not
implemented. Until it is, every strategy organises 180 passengers simultaneously, as though one
announcement gave every passenger an exact queue slot at T=0. Strict Steffen currently wins on total
time under that assumption.

Implementing the call model raises the earliest possible Strict Steffen readiness from its present
03:44 to at least 11:56. The published numbers therefore change, and the video must be produced after
the change, not before. No deliverable that quotes a timing may be built until Part 1 is complete and
the default comparison has been rebuilt.

The outcome of the corrected comparison is not assumed here. Whatever the simulation produces is what
gets published.

## Part 1 — Controlled line formation

Implements the approved line-formation spec. That document remains normative; this section defines
only the mechanism.

### Release rules

Preparation gains an explicit gate-agent call. A passenger becomes *eligible* at a release time, and
only then does the existing behaviour model govern response, walking, crowding, mistakes, correction
and staging.

| Strategy | Release mode | Release time for a passenger |
|---|---|---|
| Random (`random_front`) | `general` | `0.0` for every passenger |
| Back-to-front (`back_to_front_zones`) | `cohort` | `cohort_index × zoneIntervalSeconds` |
| Strict Steffen (`strict_steffen`) | `individual` | `boarding_rank × passengerIntervalSeconds` |

`cohort_index` is the position of the passenger's `prep_cohort` among that strategy's distinct
cohort values sorted ascending, so cohorts need not be contiguous. For `back_to_front_zones`,
`_zone_back_to_front(row) = (30 - row) // 5` already makes cohort `0` the rear-most five rows, so
ascending cohort order releases the aircraft from the back forward as specified.

`boarding_rank` is already assigned `0…179` in exact Steffen order by
`apply_companion_policy` under the `separate` companion policy. With a four-second interval the last
passenger is called at `179 × 4 = 716 s = 11:56`, matching the documented lower bound.

Release times are pure functions of the strategy and the passenger's rank. They consume no random
numbers, so determinism for a given seed is unaffected.

### Strategy declaration

`Strategy` gains a `release_mode` field with values `general`, `cohort` or `individual`. The default
is derived rather than hand-set on every strategy: `general` when `prep_cohorts <= 1`, otherwise
`cohort`. `strict_steffen` declares `individual` explicitly. Existing expert strategies keep working
under the derived default without individual edits.

### Calibration values

`config/behaviour-calibration.json` gains:

```json
"preparationRelease": {"zoneIntervalSeconds": 20.0, "passengerIntervalSeconds": 4.0}
```

Both values get `config/parameter-registry.json` entries in the `provisional` display category. They
are named scenario assumptions, not observed gate-agent rates.

### Gating

In the preparation loop, a passenger whose release time has not been reached may not transition to
`moving`. The activation-utility draw is skipped entirely for that passenger, so no random numbers
are consumed on their behalf before release.

An uncalled passenger remains `waiting` or `standing` and continues to accumulate frustration through
the existing waiting path. That accumulation is the point of the change: the wait for a call is a
real cost the previous model gave away for free.

### Events

Recorded at their modelled times, in addition to existing preparation events:

- `preparation_general_call` — once at `0.0`, `passenger_id` `None`, details `{"passenger_count": n}`;
- `preparation_zone_called` — once per cohort at its release time, `passenger_id` `None`, details
  `{"cohort": c, "passenger_count": k}`;
- `preparation_passenger_called` — once per passenger at that passenger's release time, with
  `passenger_id` set.

`preparation_started` keeps its existing meaning: the moment a passenger responds and begins moving.
The gap between a passenger's call and their `preparation_started` is response time, and remains
governed by the existing decision model.

`SimulationEvent.passenger_id` is already optional, so no model change is required for the two
gate-level events.

### Preparation cap

`maxPreparationSeconds` stays at `1800`. If Strict Steffen fails to complete preparation within that
cap, the run is reported as timed out — a modelled outcome, not a failure. In that case the work
stops and the cause is investigated. The cap is not raised to force a completed race.

### Rebuild

`scripts/build_default_comparison.py` reruns the 100-run comparison and regenerates
`web/data/default-comparison.json` so the shipped default reflects the corrected model.

## Part 2 — Per-lane frustration and capture mode

### Live frustration per lane

Each of the three lane labels gains a live model-predicted frustration figure shown as a whole
percentage from 0 to 100, coloured by the existing `frustrationVisual` scale and updated on every
frame.

The displayed value is the serialized current mean frustration multiplied by 100 — the same source
already used by the live table's frustration cell. No new derivation is introduced, and the figure is
the current index, never the accumulated burden.

The lane key stays `aria-hidden="true"`. The live table remains in the DOM and remains the
accessible source of the same numbers, matching the pattern already established for the canvas.

### Capture mode

A `?capture=1` query parameter puts the page into a recording layout by setting a class on `<body>`.
Without the parameter the page is unchanged.

Capture mode keeps: the brand line, master clock, gate/queue/aircraft axis, the three lanes with
their frustration figures, the canvas, and the frustration legend including its `model-predicted`
label. It hides the site header, premise, playback controls, passenger inspector, live table,
scenario controls, expert workspace, methodology and footer, and sizes the stage to 1080×1350.

Two further parameters serve the recorder and are inert otherwise:

- `?speed=<n>` sets the timeline rate to any positive number. `createTimeline.setSpeed` already
  accepts arbitrary positive values, so no cap needs lifting.
- `?autoplay=1` starts playback once the default comparison has loaded.

A `data-capture-stage` attribute on `<body>` selects what is visible: `race` during the race,
`result` for the closing card. The recording script switches it; CSS does the rest.

## Part 3 — The LinkedIn video

`scripts/render_linkedin_video.sh` starts the local server, drives Playwright, stops the server and
converts the recording. It is repeatable: when a number changes, the script is rerun rather than the
video rebuilt by hand.

- Viewport and recording size 1080×1350, device scale factor 1.
- Playback speed computed as `race_duration_seconds / 34`, where `race_duration_seconds` is the
  longest `replay.ends_at_seconds` across the three strategies — the same duration the timeline uses.
  The race therefore always occupies about 34 seconds regardless of how long the corrected
  simulation runs.
- After the timeline ends, `data-capture-stage` switches to `result` and the closing card is held for
  about 6 seconds, giving roughly 40 seconds total.
- The Playwright `webm` is converted with ffmpeg to H.264, `yuv420p`, 30 fps, `+faststart`, which is
  what LinkedIn expects.
- Outputs `output/boarding-frustration-linkedin.mp4` and a poster PNG taken from the held result
  frame.

`output/` stays git-ignored as generated material. The poster is copied to `docs/media/` and
committed so the README can show a still without carrying the video binary.

## Part 4 — Research collection

A new `RESEARCH.md` at the repository root, added to `PUBLIC_DOCUMENTS` in `boarding_sim/server.py`
so it is served alongside the existing methodology documents, and linked from the methodology
section.

Roles are kept distinct to avoid two overlapping source lists:

- `SOURCES.md` stays normative — which source justifies which model parameter, aligned with the
  parameter registry.
- `RESEARCH.md` is the readable collection, and links to `SOURCES.md` for parameter-level detail.

`RESEARCH.md` separates four tiers, so a reader can see how much weight each claim carries:

1. **Measured** — field-calibrated aircraft mechanics from the Schultz lineage, with the specific
   parameters this model takes from each paper.
2. **Research-informed structure** — heterogeneous delay tolerance, dynamic reference points, group
   behaviour, evolving impatience. Structure only; no coefficients transferred.
3. **Assumptions of this model** — gate geometry, the twenty-second zone interval, the four-second
   individual call rate, the preparation frustration coefficients, and the 0.25 companion-separation
   stress shock. Labelled as the author's assumptions, not findings.
4. **Real-world observations** — what airlines and experimenters have actually measured when these
   methods were tried. Explicitly context, and explicitly *not* used to calibrate this model.

It also carries a plain-language explanation of Random, Back-to-front, WILMA, and both Steffen
variants, so a non-specialist reader can follow the comparison.

Tier 4 requires web research. Every claim in it carries a citation to a source that can be checked.
Anything that cannot be sourced is left out rather than softened.

## Part 5 — Open-source repository preparation

- Project renamed to **`boarding-lab`** in `pyproject.toml` and `package.json`, and in the README
  title. The Python package directory stays `boarding_sim`; renaming it would churn every import for
  no reader benefit.
- `LICENSE` — MIT, `Copyright (c) 2026 Dennis Kefalas`.
- `CITATION.cff` so the simulator can be cited properly.
- `CONTRIBUTING.md` — short: how to run the suite, and the rule that provisional coefficients may not
  be relabelled as calibrated without validation evidence.
- `README.md` rewritten for a stranger rather than for a handoff: what this is, what it is not, how
  to run it, and where the evidence boundary sits.
- `CODEX_PROMPT.md` moves to `docs/archive/`.
- The superseded JavaScript prototype moves from `src/` to `reference/legacy-js/src/`, and
  `tests/simulation.test.mjs` moves with it to `reference/legacy-js/tests/`. The relative import
  `../src/simulation.js` still resolves. `package.json`'s test script becomes
  `node --test tests/*.test.mjs reference/legacy-js/tests/*.test.mjs` so no test is lost from the
  suite.
- Verified from a fresh clone into a temporary directory: the Python suite passes, the Node suite
  passes, and the server boots and serves the page.

Nothing is created on GitHub and nothing is pushed. The deliverable is a local repository in a state
where the author can publish it with a single decision of their own.

## Evidence and honesty boundary

Unchanged from the Boarding Lab design, and binding on all three deliverables:

- Aircraft mechanics may be described as literature-backed and tested.
- Preparation and frustration outputs must be described as **model-predicted** and provisional.
- The video carries the `model-predicted` label in its legend, in frame, for its whole duration.
- No deliverable may claim validated passenger psychology or make an operational recommendation.

One dependency is called out explicitly because it drives the story: Strict Steffen's frustration
result depends on the provisional `companionSeparationShock` of 0.25 applied to passengers the method
separates from their companions. That value is an assumption. `RESEARCH.md` states it in tier 3, and
the LinkedIn post copy should own it rather than leave it to be discovered.

## Verification and acceptance

Existing Python, Node and Playwright suites must stay green throughout.

New automated checks:

- an uncalled Strict Steffen passenger cannot enter `moving`;
- `preparation_passenger_called` events occur in exact boarding order at four-second intervals;
- Strict Steffen preparation cannot finish before its final passenger call;
- back-to-front cohorts are released at twenty-second intervals, rear cohort first;
- Random receives exactly one `preparation_general_call` at `0.0` and no per-zone or per-passenger
  calls;
- identical scenario and seed still produce byte-equivalent results;
- both new calibration values resolve through the parameter registry as `provisional`;
- the lane frustration figure equals the serialized current mean multiplied by 100 and rounded;
- capture mode hides the controls and live table, and its absence leaves the page unchanged;
- the render script produces a playable H.264 MP4 of the expected dimensions.

Manual acceptance:

- watch the rendered video start to finish and confirm the long line-formation period is visible,
  the three lanes are legible, the frustration figures move, and the closing card is readable;
- confirm the page is unchanged for a normal visitor;
- confirm a fresh clone runs.

## Scope limits

This work does not:

- claim validated passenger psychology or make operational recommendations;
- change the A320 180-seat reference aircraft or the modelled boundary at T=0;
- model public-address intelligibility, multiple gate agents, absent passengers, or boarding-pass
  verification during line formation;
- integrate into FlyByCode or deploy a public URL;
- create a GitHub repository, push, or publish anything;
- write the LinkedIn post copy itself, beyond reporting the numbers and caveats the author needs.
