import test from 'node:test';
import assert from 'node:assert/strict';

import {conclusionFor} from '../web/js/results.js';


test('timed-out comparisons do not declare a winner', () => {
  assert.equal(conclusionFor({
    strategy_order: ['a'],
    strategies: {a: {status: 'timed_out'}},
    winner: 'a',
  }).winner, null);
});

test('valid conclusion uses the server-provided winner', () => {
  const conclusion = conclusionFor({
    strategy_order: ['strict_steffen', 'random_front'],
    strategies: {
      strict_steffen: {status: 'valid'},
      random_front: {status: 'valid'},
    },
    winner: 'strict_steffen',
  });
  assert.equal(conclusion.winner, 'strict_steffen');
  assert.match(conclusion.headline, /Strict Steffen/);
});
