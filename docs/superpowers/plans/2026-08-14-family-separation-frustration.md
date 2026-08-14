# Family-Separation Frustration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a strong, transparent, provisional frustration penalty when Strict Steffen separates family members, then regenerate the comparison and LinkedIn video.

**Architecture:** Strategy assignment already identifies passengers whose companions are separated. Preparation will apply one named event shock to those passengers only when the strategy's companion policy is `separate`; the existing stress-to-frustration mapping and burden integration will carry the effect through all outputs. The web artifact and video will then be rebuilt from the updated model.

**Tech Stack:** Python 3.11 simulation and `unittest`, JSON calibration/provenance, browser replay, Playwright capture, FFmpeg H.264 export.

---

### Task 1: Specify separated-family behavior with failing tests

**Files:**
- Modify: `tests/test_preparation.py`
- Modify: `tests/test_comparison.py`

- [ ] **Step 1: Write the focused unit test**

Add imports for `copy`, `assign_strategy`, `generate_manifest`, and `apply_companion_separation_shock`. Create the same manifest under Random and Strict Steffen, capture pre-shock loads, and assert:

```python
strict_events = apply_companion_separation_shock(
    strict_passengers, strategy_by_id("strict_steffen"), self.calibration
)
random_events = apply_companion_separation_shock(
    random_passengers, strategy_by_id("random_front"), self.calibration
)
affected = [p for p in strict_passengers if p.family_id and p.companion_override]
self.assertTrue(affected)
self.assertEqual(len(strict_events), len(affected))
self.assertFalse(random_events)
for passenger in affected:
    self.assertAlmostEqual(
        passenger.stress_load,
        strict_before[passenger.id] + 0.25,
    )
    self.assertGreater(passenger.frustration, strict_frustration_before[passenger.id])
```

- [ ] **Step 2: Write the comparison-level event test**

Run one fair comparison and assert that `companion_separation_shock` events occur only for Strict Steffen and match its separated-passenger count:

```python
comparison = run_comparison({}, seed=20260841)
for strategy_id in ("random_front", "back_to_front_zones"):
    events = comparison["strategies"][strategy_id]["phases"]["part2_preparation"]["events"]
    self.assertFalse(any(event["type"] == "companion_separation_shock" for event in events))
strict = comparison["strategies"]["strict_steffen"]
events = strict["phases"]["part2_preparation"]["events"]
self.assertEqual(
    sum(event["type"] == "companion_separation_shock" for event in events),
    strict["metrics"]["companion_overrides"],
)
```

- [ ] **Step 3: Run the tests and verify the intended failure**

Run:

```bash
python3 -m unittest tests.test_preparation tests.test_comparison -v
```

Expected: import failure because `apply_companion_separation_shock` does not yet exist.

### Task 2: Apply the calibrated event shock

**Files:**
- Modify: `boarding_sim/preparation.py`
- Modify: `config/behaviour-calibration.json`
- Modify: `config/parameter-registry.json`
- Modify: `boarding_sim/engine.py`

- [ ] **Step 1: Add the provisional coefficient and provenance**

Add this calibration leaf:

```json
"companionSeparationShock": 0.25
```

Register `behaviour.companionSeparationShock` as `UNCALIBRATED_HUMAN_BEHAVIOUR`, category `provisional`, with the note that it is a one-time latent-stress event requiring Layer 4 calibration.

- [ ] **Step 2: Implement the minimal separation-shock function**

Import `frustration_from_load` and add:

```python
def apply_companion_separation_shock(passengers, strategy, calibration):
    if strategy.companion_policy != "separate":
        return []
    shock = calibration["companionSeparationShock"]
    events = []
    for passenger in passengers:
        if not passenger.family_id or not passenger.companion_override:
            continue
        passenger.stress_load = clamp(passenger.stress_load + shock, 0.0, 2.0)
        passenger.frustration = frustration_from_load(passenger, calibration)
        passenger.peak_frustration = max(passenger.peak_frustration, passenger.frustration)
        events.append(SimulationEvent(
            "companion_separation_shock", 0.0, passenger.id,
            {"stress_load_shock": shock},
        ))
    return events
```

Invoke it before the initial preparation snapshot, preserving the event list so live replay begins with the higher frustration state.

- [ ] **Step 3: Bump the behavioral model version**

Change `MODEL_VERSION` from `pbs-v2-python-1.1.0` to `pbs-v2-python-1.2.0`; the result schema remains unchanged.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_preparation tests.test_comparison tests.test_foundation -v
```

Expected: all tests pass and parameter-registry coverage remains valid.

- [ ] **Step 5: Commit the model correction**

```bash
git add boarding_sim/preparation.py boarding_sim/engine.py config/behaviour-calibration.json config/parameter-registry.json tests/test_preparation.py tests/test_comparison.py
git commit -m "fix: model frustration from family separation"
```

### Task 3: Rebuild and verify the public comparison

**Files:**
- Modify: `web/data/default-comparison.json`

- [ ] **Step 1: Rebuild 100 fair comparisons**

Run:

```bash
python3 scripts/build_default_comparison.py --workers 4
```

Expected: 100 comparisons complete and a new canonical artifact is written.

- [ ] **Step 2: Verify reconciliation and public behavior**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -q
npm test
```

Expected: all Python and JavaScript tests pass. Inspect the representative result and report preparation, boarding, and total F·minutes without assuming the winner.

- [ ] **Step 3: Commit the rebuilt artifact**

```bash
git add web/data/default-comparison.json
git commit -m "data: rebuild comparison with separation burden"
```

### Task 4: Export and inspect the replacement LinkedIn video

**Files:**
- Replace: `output/boarding-comparison-linkedin.mp4`
- Replace: `output/boarding-comparison-linkedin-poster.png`

- [ ] **Step 1: Capture the updated browser replay**

Start the local application on port 8765, load the rebuilt representative comparison, capture the existing 1080×1350 race layout for about 15 seconds, and reveal the updated final result card after the three lanes finish.

- [ ] **Step 2: Encode the delivery MP4**

Run:

```bash
ffmpeg -y -i output/boarding-comparison-linkedin.webm \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -movflags +faststart -an output/boarding-comparison-linkedin.mp4
```

- [ ] **Step 3: Verify the complete media file and proof frames**

Run:

```bash
ffmpeg -v error -i output/boarding-comparison-linkedin.mp4 -f null -
ffprobe -v error -show_entries stream=codec_name,width,height,pix_fmt \
  -show_entries format=duration,size output/boarding-comparison-linkedin.mp4
```

Expected: complete decode with no errors, H.264/yuv420p, 1080×1350, plausible 14–17 second duration. Inspect opening, mid-race, and final frames; final wording must say `lowest modeled total in this run` if a winner exists.

### Task 5: Final handoff

- [ ] **Step 1: Confirm repository and artifact state**

Run `git status --short`, distinguish pre-existing unrelated changes from this correction, and confirm the MP4 and poster exist and are non-empty.

- [ ] **Step 2: Report the outcome**

Provide clickable links to the MP4 and poster, the actual duration and size, and the updated strategy totals. State that the `0.25` family-separation shock remains a provisional assumption.
