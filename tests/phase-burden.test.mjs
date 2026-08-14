import test from 'node:test';
import assert from 'node:assert/strict';
import {phaseBurden} from '../web/js/phase-burden.js';

const STRICT_STEFFEN = {preparationEndsAt: 766, preparationCheckpoint: 5.24};

test('during preparation everything accumulated belongs to preparation', () => {
  const split = phaseBurden({...STRICT_STEFFEN, time: 600, runningBurden: 4.16});
  assert.equal(split.preparation, 4.16);
  assert.equal(split.boarding, 0);
});

test('preparation freezes at its checkpoint once the line is formed', () => {
  const split = phaseBurden({...STRICT_STEFFEN, time: 1000, runningBurden: 6.57});
  assert.equal(split.preparation, 5.24);
  assert.ok(Math.abs(split.boarding - 1.33) < 1e-9);
});

test('the two phases always sum to the running total', () => {
  for (const [time, running] of [[60, 0.29], [766, 5.24], [1300, 8.0], [1500, 8.41]]) {
    const split = phaseBurden({...STRICT_STEFFEN, time, runningBurden: running});
    assert.ok(
      Math.abs(split.preparation + split.boarding - running) < 1e-9,
      `phases must sum to ${running} at t=${time}`,
    );
  }
});

test('neither phase ever goes backwards as the clock advances', () => {
  const samples = [[60, 0.29], [300, 1.86], [766, 5.24], [1000, 6.57], [1500, 8.41]];
  let previous = {preparation: 0, boarding: 0};
  for (const [time, running] of samples) {
    const split = phaseBurden({...STRICT_STEFFEN, time, runningBurden: running});
    assert.ok(split.preparation >= previous.preparation, `preparation fell at t=${time}`);
    assert.ok(split.boarding >= previous.boarding, `boarding fell at t=${time}`);
    previous = split;
  }
});

test('a running total below the checkpoint never produces negative boarding', () => {
  const split = phaseBurden({...STRICT_STEFFEN, time: 900, runningBurden: 5.0});
  assert.equal(split.boarding, 0);
});

test('missing values report nothing rather than zero', () => {
  const split = phaseBurden({
    preparationEndsAt: 766,
    preparationCheckpoint: 5.24,
    time: 900,
    runningBurden: null,
  });
  assert.equal(split.preparation, null);
  assert.equal(split.boarding, null);
});
