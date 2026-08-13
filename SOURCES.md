# Research sources used for the model structure

## Aircraft boarding core

### Michael Schultz — Field Trial Measurements to Validate a Stochastic Aircraft Boarding Model
Aerospace 2018, 5(1), 27. DOI: 10.3390/aerospace5010027

Supports:

- stochastic, discrete passenger boarding model;
- 0.4 m × 0.4 m cabin cells;
- individual passenger properties;
- 0.8 m/s model aisle speed setting;
- field measurement of aircraft-door arrivals;
- Weibull baggage storage time with shape 1.7 and scale 16.0 s;
- seat-interference/seat-shuffle logic;
- real A320/B737 field calibration and validation.

Official article: https://www.mdpi.com/2226-4310/5/1/27

### Michael Schultz — Fast Aircraft Turnaround Enabled by Reliable Passenger Boarding
Aerospace 2018, 5(1), 8. DOI: 10.3390/aerospace5010008

Supports:

- forward-directed stochastic discrete boarding process;
- aircraft grid approach;
- one-passenger-per-cell movement;
- passenger-specific luggage and arrival effects;
- importance of passenger conformance and arrival availability.

Official article: https://www.mdpi.com/2226-4310/5/1/8

### Schultz et al. — Evaluation of Aircraft Boarding Scenarios Considering Reduced Transmission Risks
Sustainability 2020, 12(13), 5329. DOI: 10.3390/su12135329

Supports continued use of the 0.4 m grid and stochastic passenger-level boarding scenario evaluation.

Official article: https://www.mdpi.com/2071-1050/12/13/5329

## Groups / companion compatibility

### Shen et al. — Group boarding for airplanes: benchmarking static policies and optimizing dynamic assignment with deep reinforcement learning
arXiv:2607.21512, 2026.

Supports explicitly keeping companions together when assessing boarding policies and evaluating group-size/luggage variation.

Preprint: https://arxiv.org/abs/2607.21512

## Delay heterogeneity and dynamic expectations

### Jiang et al. — Model of passenger behavior choice under flight delay based on dynamic reference point
Journal of Air Transport Management 75 (2019), 51–60.

Supports:

- heterogeneous passenger delay tolerance;
- dynamic reference points;
- influence of punctuality requirements;
- influence of trust in delay information;
- different behaviour under the same delay scenario.

DOI: 10.1016/j.jairtraman.2018.11.008

## Psychological impatience / CA structure

### A dynamic impatience-determined cellular automata model for evacuation dynamics
Simulation Modelling Practice and Theory (2019).

Supports the general modelling idea that an internal impatience state can evolve and feed back into movement/update behaviour.

Important limitation: this is evacuation research, not normal airline boarding. Its coefficients are **not** transferred into this application.

ScienceDirect article: https://www.sciencedirect.com/science/article/pii/S1569190X19300371

## Interpretation rule

These sources justify model **structure** and selected aircraft parameters. They do not validate the current gate-frustration coefficients. The parameter registry is the authority for what may be labelled calibrated.
