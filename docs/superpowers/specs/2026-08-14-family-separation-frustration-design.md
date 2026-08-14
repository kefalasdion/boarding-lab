# Family-separation frustration correction

## Purpose

Correct the provisional frustration model so that a boarding strategy which genuinely separates family or companion-group members carries an explicit human cost. The present model records separation under theoretical Strict Steffen but does not convert that event into passenger stress or frustration.

## Behavior

- A passenger receives a one-time separation shock when the selected strategy has a `separate` companion policy and that passenger's family is split by the boarding order.
- The default provisional shock is `0.25` latent-stress units.
- The shock is applied at the start of gate preparation, when the passenger learns that the group must separate.
- The existing logistic mapping converts the higher stress load into the live 0–100 frustration index.
- Existing time integration then adds the effect to preparation and total frustration burden in F·minutes. No fixed surcharge is added after simulation.
- Strategies that preserve companions do not receive the shock. A companion-order override that keeps a family together is not treated as separation.
- The event and coefficient remain explicitly provisional and must not be described as measured or validated passenger behavior.

## Model and data changes

- Add a named `companionSeparationShock` coefficient to the behavior-calibration file and parameter registry.
- Apply the shock in preparation only to passengers who are both members of a family group and flagged as separated under a `separate` companion policy.
- Record a `companion_separation_shock` simulation event for each affected passenger so the assumption is auditable.
- Keep the existing `companion_overrides` metric for compatibility; do not reinterpret non-separating overrides as separation.

## Verification

- A focused test must first demonstrate the current missing behavior.
- A separated family member must begin preparation with higher stress/frustration than the same passenger under a companion-preserving strategy.
- Passengers without a family, and family members kept together, must receive no separation event or shock.
- Preparation burden, embarkation burden, and total burden must continue to reconcile.
- After the model tests pass, regenerate the representative comparison and LinkedIn video. Report the new values without assuming which strategy wins.

## Scope

This change does not claim to calibrate the magnitude from passenger research, model staff conflict, or track minute-by-minute family proximity. Those would require evidence beyond this hobby visualization. The `0.25` shock is a transparent, configurable scenario assumption chosen to represent a strong effect.
