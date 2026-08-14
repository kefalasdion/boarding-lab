import test from 'node:test';
import assert from 'node:assert/strict';

import { frustrationVisual } from '../web/js/frustration-scale.js';


test('frustration scale has five stable non-color labels', () => {
  assert.equal(frustrationVisual(0.05).label, 'Calm');
  assert.equal(frustrationVisual(0.25).label, 'Low');
  assert.equal(frustrationVisual(0.45).label, 'Raised');
  assert.equal(frustrationVisual(0.65).label, 'Elevated');
  assert.equal(frustrationVisual(0.90).label, 'High');
});

test('high threshold has a non-color label and ring flag', () => {
  assert.deepEqual(frustrationVisual(0.75), {
    color: '#bd315e',
    label: 'High',
    aboveThreshold: true,
  });
});

test('threshold can be supplied from authoritative result data', () => {
  assert.equal(frustrationVisual(0.70, 0.65).aboveThreshold, true);
  assert.equal(frustrationVisual(0.64, 0.65).aboveThreshold, false);
});
