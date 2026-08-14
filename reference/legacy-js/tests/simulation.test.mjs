import test from 'node:test';
import assert from 'node:assert/strict';
import { runFlight } from '../src/simulation.js';
import { customSeatRuleSeconds } from '../src/aircraft-ca.js';
import { DEFAULT_SCENARIO } from '../src/config.js';

test('deterministic for same seed', () => {
  const a = runFlight({}, 4242);
  const b = runFlight({}, 4242);
  assert.equal(a.metrics.prepSeconds, b.metrics.prepSeconds);
  assert.equal(a.metrics.totalSeconds, b.metrics.totalSeconds);
  assert.equal(a.metrics.frustrationBurden.mean, b.metrics.frustrationBurden.mean);
});

test('all passengers seat in baseline', () => {
  const r = runFlight({}, 99);
  assert.equal(r.aircraft.seatedCount, 180);
  assert.equal(r.aircraft.debug.occupiedSeatCount, 180);
  assert.equal(r.metrics.timedOut, false);
  assert.ok(r.aircraft.debug.maxAisleOccupancy <= r.aircraft.debug.aisleCells);
});

test('custom 15 second occupancy rule increments at 60 percent', () => {
  const c = DEFAULT_SCENARIO.boarding;
  assert.equal(customSeatRuleSeconds(.59, c), 15);
  assert.equal(customSeatRuleSeconds(.60, c), 20);
  assert.equal(customSeatRuleSeconds(.70, c), 25);
  assert.equal(customSeatRuleSeconds(.80, c), 30);
  assert.equal(customSeatRuleSeconds(.90, c), 35);
});

test('split two-door strategy uses both doors', () => {
  const r = runFlight({access:{mode:'bus'},boarding:{strategy:'split_half_two_door'}}, 771);
  const entries = r.aircraft.events.filter(e=>e.type==='entered');
  assert.ok(entries.some(e=>e.door==='front'));
  assert.ok(entries.some(e=>e.door==='rear'));
  assert.equal(r.aircraft.seatedCount,180);
});

test('field service model and user service model are separate', () => {
  const field = runFlight({boarding:{serviceModel:'field_calibrated'}}, 812);
  const custom = runFlight({boarding:{serviceModel:'user_occupancy_rule'}}, 812);
  assert.notEqual(field.metrics.cabinBoardingSeconds, custom.metrics.cabinBoardingSeconds);
});
