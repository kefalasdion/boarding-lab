# Contributing to Boarding Lab

Contributions are welcome, particularly real observational data — that is what this project is short
of.

## Running the suites

```bash
python3 -m unittest discover -s tests -p 'test_*.py'   # simulation, API and asset contracts
npm test                                                # browser modules and the legacy reference
npx playwright test                                     # end-to-end browser experience
```

`npm run test:all` runs all three. No application packages are required for the Python suite; Node
dependencies are only needed for the browser tests and the video render.

## The one rule that matters

**A value may not move from `provisional` to `calibrated` without validation evidence.**

Every configurable value carries a provenance record in
[`config/parameter-registry.json`](config/parameter-registry.json). The registry is enforced by tests:
a value present in configuration but missing from the registry fails the suite, as does a registry
entry whose value has drifted from the configuration.

The categories mean specific things:

- `calibrated` — validated against field measurement in a cited published source;
- `literature` — taken from a published model without independent revalidation here;
- `provisional` — an assumption of this model, not an observation;
- `operational` / `user` — scenario inputs, not behavioural claims.

If you want to promote a coefficient, the path is [`VALIDATION_PLAN.md`](VALIDATION_PLAN.md): supply
the observation, record it, and change the category in the same change that changes the number. A
pull request that relabels a coefficient without evidence will be declined. The credibility of every
result in this repository depends on that boundary holding.

## Architecture boundaries

- **Python is the single simulation authority.** Browser code renders serialized results. It may not
  reproduce strategy rules, frustration formulas, luggage distributions, movement rules or the
  readiness policy.
- **Every run needs an explicit 32-bit integer seed.** Identical scenario and seed must produce
  byte-equivalent output; there are tests for this.
- **Timeouts are modelled outcomes, not errors.** A strategy that fails to finish is reported as
  timed out. Never widen a safety limit to make a run complete.
- `reference/legacy-js/` holds the superseded JavaScript V2 prototype. It is kept for provenance and
  still runs in the suite, but it is not the model. Do not add features there.

## Style

Match the surrounding code. The Python uses standard library only and type hints throughout; the
browser code is vanilla ES modules with no framework and no build step.
