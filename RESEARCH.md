# Research behind Boarding Lab

Boarding Lab asks one question: **a smarter boarding order may fill the cabin faster, but is it still
better once you count the time and passenger cost of creating that order?** Almost every published
boarding comparison starts its clock when the first passenger walks through the aircraft door. This
simulator starts it earlier — at the announcement to prepare for boarding — because the work of
sorting 180 people into a sequence has to happen somewhere, and it happens to the passengers.

This document collects what the model rests on. It does not claim to have measured passenger
frustration. It claims to have modelled it, transparently, and to have kept the measured parts and
the assumed parts clearly apart.

## How to read this document

Every input to this simulator falls into one of four tiers. The tier decides how much weight a
conclusion drawn from it can carry.

| Tier | What it means | Can it support a public claim? |
|---|---|---|
| 1 · Measured | Field-observed, published, and validated against real aircraft turnarounds | Yes, as published |
| 2 · Research-informed structure | The *shape* of the mechanism comes from published work; no coefficients are transferred | Yes, as a modelling choice |
| 3 · Assumptions of this model | Chosen by the author to make the model runnable. Not observed | No — these are labelled model-predicted and provisional |
| 4 · Real-world observations | What has actually been measured when these methods were tried | Yes, as context — but these did **not** calibrate this model |

The parameter-level authority is [`config/parameter-registry.json`](config/parameter-registry.json),
which records a provenance category for every configurable value.
[`SOURCES.md`](SOURCES.md) maps each source to the specific parameters it justifies.
[`VALIDATION_PLAN.md`](VALIDATION_PLAN.md) defines what would have to happen for a tier 3 value to
be promoted.

## The boarding methods in plain language

**Random.** Passengers are given assigned seats but no boarding order. One announcement, one loose
queue, first come first served. This is what many airlines effectively do once their priority groups
have boarded.

**Back-to-front.** The cabin is split into zones — six five-row zones here — and the zones are called
from the rear of the aircraft forward. It is the most widely used method, and, as tier 4 below shows,
repeatedly the slowest one measured.

**WILMA (outside-in).** Window seats first, then middle, then aisle. It attacks the real bottleneck:
a seated passenger having to stand up and step into the aisle so someone can get past them. United
Airlines adopted it across its network in October 2023.

**Practical Steffen.** Steffen's alternating pattern, relaxed so that people travelling together stay
together. Available in this simulator's expert workspace.

**Strict Steffen.** The theoretical optimum: window seats first, then middle, then aisle; within each
of those, alternating rows and alternating sides of the aircraft; ordered back to front. Every
passenger has exactly one slot in one queue. Two people sitting next to each other are, by
construction, nowhere near each other in the line. No airline uses it.

## Tier 1 — Measured

Everything here is field-observed and published. This is the part of the simulator that behaves like
a real aircraft.

### Michael Schultz, *Field Trial Measurements to Validate a Stochastic Aircraft Boarding Model*
Aerospace 2018, 5(1), 27. DOI [10.3390/aerospace5010027](https://doi.org/10.3390/aerospace5010027)

Measured during real Airbus A320 and Boeing 737 turnarounds, in cooperation with the airlines, ground
handlers and airport operators. Passenger arrival times were recorded at the aircraft door; hand
luggage storage times and seat-shuffle interactions were recorded from inside the cabin. The
resulting model reproduced the field measurements to within 5%.

This simulator takes from it:

- the 0.4 m × 0.4 m cabin cell grid, one passenger per aisle cell;
- 0.8 m/s maximum aisle walking speed;
- Weibull hand-luggage storage time, shape 1.7, scale 16.0 s;
- seat-interference (seat-shuffle) resolution;
- the aircraft-door minimum headway baseline of 3.7 s.

### Michael Schultz, *Fast Aircraft Turnaround Enabled by Reliable Passenger Boarding*
Aerospace 2018, 5(1), 8. DOI [10.3390/aerospace5010008](https://doi.org/10.3390/aerospace5010008)

Supports the forward-directed stochastic discrete boarding process, the aircraft grid approach, and
the importance of passenger conformance and arrival availability.

### Schultz et al., *Evaluation of Aircraft Boarding Scenarios Considering Reduced Transmission Risks*
Sustainability 2020, 12(13), 5329. DOI [10.3390/su12135329](https://doi.org/10.3390/su12135329)

Supports continued use of the 0.4 m grid and passenger-level scenario evaluation.

**Boundary:** these sources validate the *aircraft*. None of them measured anything at the gate before
boarding began, and none of them measured how passengers felt.

## Tier 2 — Research-informed structure

These sources justify the shape of a mechanism. No numerical coefficient is copied from any of them
into this simulator.

### Jiang & Ren, *Model of passenger behavior choice under flight delay based on dynamic reference point*
Journal of Air Transport Management 75 (2019), 51–60. DOI
[10.1016/j.jairtraman.2018.11.008](https://doi.org/10.1016/j.jairtraman.2018.11.008)

Supports treating delay tolerance as heterogeneous rather than uniform, with dynamic reference points,
punctuality pressure and trust in delay information all shifting how a given passenger responds to
the same delay. This is why passengers in this model carry individual tolerance thresholds and
information-trust values rather than a shared one.

### *A dynamic impatience-determined cellular automata model for evacuation dynamics*
Simulation Modelling Practice and Theory (2019). [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1569190X19300371)

Supports the general idea that an internal impatience state can evolve over time and feed back into
movement behaviour.

**Important limitation:** this is evacuation research. People leaving a threatening situation are not
people waiting to board a holiday flight. Its coefficients are **not** transferred into this
application; only the structural idea is.

### Shen et al., *Group boarding for airplanes*
arXiv [2607.21512](https://arxiv.org/abs/2607.21512) (2026)

Supports explicitly keeping companions together when assessing boarding policies, and evaluating
group-size and luggage variation — which is why family and companion relationships are first-class
objects in this model rather than an afterthought.

## Tier 3 — Assumptions of this model

**These are the author's choices, not measurements.** Every result this simulator reports about
frustration, and every result about gate preparation time, depends on them. They are labelled
`provisional` in the parameter registry and `model-predicted` everywhere in the interface.

| Assumption | Value | Registry path | What would be needed to promote it |
|---|---|---|---|
| Zone announcement interval | 20 s | `preparation.release.zoneIntervalSeconds` | Timed observations of zone calls at real gates |
| Individual passenger call rate | 4 s | `preparation.release.passengerIntervalSeconds` | Timed observation of an agent calling passengers one by one — no airline does this, so it would have to be a staged trial |
| Companion separation stress shock | 0.25 | `behaviour.companionSeparationShock` | A measured stress or self-report response from passengers separated from companions by boarding policy |
| Preparation frustration rates | uncertainty 0.055, no-progress 0.050, crowding 0.070, instruction 0.055, correction shock 0.090 per minute | `behaviour.preparationPerMinute.*` | Gate observation paired with passenger self-reports over the waiting period |
| Initial stress weights | delay 0.26, prior gate wait 0.10, dwell 0.05, uncertainty 0.16, fatigue 0.17, connection 0.18, unreliable information 0.14 | `behaviour.initial.*` | Survey or physiological measurement at T=0 |
| Gate geometry | 190 m², aspect 1.6, 0.75 m queue lane spacing | `preparation.*` | Measured layout of the target gate |

The four-second call rate deserves particular attention, because it produces the video's most
striking number. Calling 180 passengers individually cannot finish before 11 minutes 56 seconds, and
that single assumption is most of why Strict Steffen loses. It is a deliberately transparent
scenario assumption: *if* you had to call people one at a time to build a perfect queue, this is what
it would cost. It is not an observed gate-agent rate, and no published source gives one.

The companion-separation shock carries less weight than its prominence suggests. Setting it to zero
moves Strict Steffen's total burden from 8.90 to 7.47 F·min — about 16% of its own figure, or 22% of
the gap to Random. The dominant driver is simply that preparation lasts thirteen minutes.

**A model whose conclusion rests on tier 3 values is a hypothesis, not a finding.** That is what this
one is.

## Tier 4 — Real-world observations

**None of the following calibrated this model.** They are the reality check: what happened when people
actually tried these methods. Where they agree with the simulator, that is encouraging but not
validating. Where they disagree, the disagreement is recorded here rather than hidden.

### Steffen & Hotchkiss, *Experimental test of airplane boarding methods* (2012)
Journal of Air Transport Management 18(1), 64–67. DOI
[10.1016/j.jairtraman.2011.10.003](https://doi.org/10.1016/j.jairtraman.2011.10.003).
Preprint: [arXiv:1108.5211](https://arxiv.org/abs/1108.5211)

72 volunteers, ages 5 and up, in a 12-row Boeing 757 fuselage mock-up on a Southern California
soundstage. Measured boarding times:

| Method | Time |
|---|---|
| Steffen | 3:36 |
| WilMA | 4:13 |
| Random | 4:44 |
| Back-to-front | 6:11 |
| Block | 6:54 |

**Read this carefully.** The authors ran each method **once** and state an estimated 10% uncertainty
per method. Participants used their own luggage. The Steffen method was not implemented perfectly —
parent-child pairs got priority and some seat assignments went wrong. And critically for this project:
**the clock started when boarding started.** The time to organise 72 people into Steffen's exact
sequence is not in these numbers.

### MythBusters, *Plane Boarding*, first aired 21 August 2014

A mock cabin with 173 real airplane seats and real overhead bins, real flight attendants, gate-checked
luggage, and roughly 5% of participants instructed to behave awkwardly — going upstream, sitting in
the wrong seat, boarding with small children, blocking the aisle. Five methods were tested, each timed
and each scored by the participants. The times and satisfaction scores below are taken from the
Wikipedia record of the 2014 season and corroborated by secondary coverage; the widely cited
[Jalopnik write-up](https://www.jalopnik.com/mythbusters-proves-most-airlines-board-planes-all-wrong-1636981904/)
reported only four of the five.

| Method | Time | Satisfaction score |
|---|---|---|
| Random, no assigned seats | 14:07 | **−5 — the lowest** |
| WILMA | 14:55 | 102 |
| WILMA Block | 15:07 | 105 |
| Reverse Pyramid | 15:10 | **113 — the highest** |
| Back-to-front | 24:29 | 19 |

This is the only one of these experiments that measured how passengers *felt* as well as how long they
took, and it found that **the fastest method was the least liked.** See "What would change my mind"
below — this result is in direct tension with part of what this simulator concludes.

### United Airlines WILMA rollout (October 2023)

United returned to window-middle-aisle boarding across its network on 26 October 2023 after testing at
one hub and four domestic stations. The airline reported an average saving of about **two minutes per
flight** and said net promoter scores for the revised process were higher than for the process it
replaced. Reported by [CBC](https://www.cbc.ca/news/business/united-airlines-boarding-system-1.7006032)
and [Forbes](https://www.forbes.com/sites/marisagarcia/2023/10/23/united-airlines-window-to-aisle-boarding-how-much-does-it-save/).

Note the scale: an operational change that a major airline considered worth a network-wide rollout
bought roughly two minutes. Simulation studies routinely report much larger gains. The gap between
the two is the subject of this project.

### Bachmat, Erland, Jaehn & Neumann, *Air Passenger Preferences: An International Comparison Affects Boarding Theory*
Operations Research 71(3), 798–820, 2023. DOI [10.1287/opre.2021.2148](https://doi.org/10.1287/opre.2021.2148)

A survey of 1,500 air passengers drawn equally from Germany, Israel and the United States. Its central
finding is that **individual boarding time — how long *you* spend in the process — relates more
closely to passenger satisfaction than total boarding time does**, and that the two are not
necessarily correlated: a strategy can produce short individual times and a long total, or the
reverse.

This is the strongest published support for the premise of this project. Optimising the total clock is
not the same as optimising the experience, and a method that finishes the aircraft quickly can still
be doing so by making individual passengers wait longer.

### Why no airline uses Strict Steffen

Steffen himself, and subsequent coverage in
[Scientific American](https://www.scientificamerican.com/article/there-are-quicker-ways-to-board-a-plane-so-why-dont-airlines-use-them/),
attribute non-adoption to practical obstacles rather than to the arithmetic being wrong: the method
separates families and travelling companions, cannot absorb late arrivals, needs passengers requiring
assistance handled outside the sequence, depends on a perfectly ordered single-file line, and competes
with priority boarding, which airlines sell. As of the Wikipedia record, no airline has adopted it.

This project's contribution is to put a number on the first and fourth of those obstacles instead of
listing them as caveats.

## What would change my mind

Honest failure conditions for this model. Each of these would force a change, not a footnote.

1. **A gate observation showing preparation is cheap.** If real gates can assemble a strongly ordered
   queue far faster than the 4-second-per-passenger assumption implies, the central result weakens or
   disappears. This is the single most load-bearing assumption in the model.

2. **Passenger self-reports contradicting the frustration ordering.** MythBusters already points this
   way. Their fastest method (random, no assigned seats) scored lowest on satisfaction, and the
   method the participants liked most, Reverse Pyramid, was about a minute slower. This simulator concludes Random produces both the fastest
   journey and the lowest model-predicted frustration. The MythBusters result suggests that real
   passengers may dislike loose, unstructured boarding *even when it is quick* — that perceived order
   and fairness carry weight this model does not represent at all. Boarding Lab currently models the
   cost of waiting and of being separated from companions; it does not model the comfort of a process
   feeling organised. **If that comfort is real and large, Random's frustration advantage is
   overstated.**

3. **A measured companion-separation response far from 0.25.** Strict Steffen splits up 54 of 180
   passengers in the reference run. If the true stress response to that separation is near zero, its
   total burden falls from 8.90 to 7.47 F·min, closing about 22% of the gap to Random. Worth knowing,
   but on its own it would not overturn the result: the thirteen minutes of preparation would remain.

4. **Field data showing zone announcements do not stack.** The back-to-front result depends on zones
   being called at intervals rather than all at once.

5. **An ordered queue built without individual calls.** Strict Steffen is charged an individual call
   for every passenger only because this model hard-codes individual release for that one strategy.
   Real gates have formed exactly ordered lines without calling anybody by name: Southwest Airlines
   boarded roughly 175 passengers into an exact numbered order — A1 to C60, printed on the boarding
   pass, with numbered stanchions at the gate — for decades, retiring the practice in January 2026
   when it moved to assigned seating. Release Strict Steffen as grouped calls instead of individual
   ones and it wins every run in this model. That is a modelling choice doing a great deal of work,
   and it is the honest weak point of the comparison.

Until at least the first two are answered with observation, every frustration number this project
publishes is a model prediction under stated assumptions — interesting, reproducible, and unproven.
