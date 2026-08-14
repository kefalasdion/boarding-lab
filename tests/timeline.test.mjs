import test from 'node:test';
import assert from 'node:assert/strict';

import { createTimeline } from '../web/js/timeline.js';


test('clock advances according to speed and clamps at duration', () => {
  const timeline = createTimeline({duration: 100, speed: 2});
  timeline.play();
  timeline.advance(12);
  assert.equal(timeline.time(), 24);
  timeline.advance(100);
  assert.equal(timeline.time(), 100);
  assert.equal(timeline.playing(), false);
});

test('pause, seek and replay preserve one continuous clock', () => {
  const timeline = createTimeline({duration: 90});
  timeline.seek(35);
  timeline.play();
  timeline.advance(5);
  timeline.pause();
  assert.equal(timeline.time(), 40);
  timeline.seek(-20);
  assert.equal(timeline.time(), 0);
  timeline.seek(200);
  assert.equal(timeline.time(), 90);
});

test('reduced motion advances one authoritative event at a time', () => {
  const timeline = createTimeline({
    duration: 100,
    reducedMotion: true,
    eventTimes: [0, 12, 31, 100],
  });
  timeline.play();
  timeline.advance(10);
  assert.equal(timeline.time(), 12);
  assert.equal(timeline.playing(), false);
  timeline.seek(25);
  assert.equal(timeline.time(), 31);
});
