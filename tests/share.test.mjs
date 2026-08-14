import test from 'node:test';
import assert from 'node:assert/strict';

import {resultUrl, summaryText} from '../web/js/share.js';


test('share URL preserves seed and public scenario inputs', () => {
  const url = resultUrl('https://example.test/lab', {seed: 42, delayMinutes: 20});
  assert.equal(url, 'https://example.test/lab?seed=42&delay=20');
});

test('share URL ignores unknown values and stays deterministic', () => {
  const first = resultUrl('https://example.test/lab?old=1', {bags: 75, secret: 'no', seed: 8});
  const second = resultUrl('https://example.test/lab', {seed: 8, secret: 'different', bags: 75});
  assert.equal(first, second);
  assert.equal(first, 'https://example.test/lab?seed=8&bags=75');
});

test('plain-language share summary keeps the scientific caveat', () => {
  const text = summaryText({winnerLabel: 'Strict Steffen', totalTime: '14:35', seed: 42});
  assert.match(text, /model-predicted/);
  assert.match(text, /provisional/);
  assert.match(text, /Strict Steffen/);
});
