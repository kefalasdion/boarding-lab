import {test, expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';


test('default comparison loads with synchronized lanes and evidence-aware results', async ({page, request}) => {
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('Ready · same passengers and one continuous clock')).toBeVisible();
  await expect(page.locator('#result-headline')).toContainText(/completes the whole journey first|No overall winner/);
  await expect(page.locator('#timing-table')).toContainText('Preparation finished at');
  await expect(page.locator('#timing-table')).toContainText('Boarding started at');
  await expect(page.locator('#timing-table')).toContainText('Boarding finished at');
  await expect(page.locator('#timing-table')).toContainText('Frustration accumulated during preparation');

  const artifact = await (await request.get('/data/default-comparison.json')).json();
  const comparison = artifact.representative;
  const eventTimes = comparison.strategy_order.flatMap((strategyId) => {
    const result = comparison.strategies[strategyId];
    return [result.metrics.timings_seconds.preparation, result.phases.part3_embarkation.aircraft.first_entry_time_seconds];
  }).sort((a, b) => a - b);
  const candidates = eventTimes.slice(0, -1).map((time, index) => (time + eventTimes[index + 1]) / 2);
  const phaseAt = (result, time) => time < result.metrics.timings_seconds.preparation
    ? 'Preparing at gate'
    : time < result.phases.part3_embarkation.aircraft.first_entry_time_seconds
      ? 'Moving to aircraft'
      : 'Boarding aircraft';
  const staggeredTime = candidates.find((time) => new Set(
    comparison.strategy_order.map((strategyId) => phaseAt(comparison.strategies[strategyId], time)),
  ).size >= 2);
  expect(staggeredTime).toBeDefined();
  expect(new Set(comparison.strategy_order.map((strategyId) => comparison.strategies[strategyId].metrics.timings_seconds.preparation)).size).toBe(3);
  expect(new Set(comparison.strategy_order.map((strategyId) => comparison.strategies[strategyId].phases.part3_embarkation.aircraft.first_entry_time_seconds)).size).toBe(3);
  const seekTime = Math.round(staggeredTime);
  await page.locator('#timeline-scrubber').fill(String(seekTime));
  for (const [strategyId, rowId] of [
    ['random_front', '#lane-random-live'],
    ['back_to_front_zones', '#lane-back-to-front-live'],
    ['strict_steffen', '#lane-strict-steffen-live'],
  ]) await expect(page.locator(rowId)).toContainText(phaseAt(comparison.strategies[strategyId], seekTime));

  const accessibility = await new AxeBuilder({page}).analyze();
  expect(accessibility.violations.filter((item) => ['serious', 'critical'].includes(item.impact))).toEqual([]);
  expect(errors).toEqual([]);
});


test('modeled preparation timeout has no winner or boarding events', async ({request}) => {
  const response = await request.post('/api/compare', {
    data: {
      scenario: {aircraft: {loadFactor: 0.05}, preparation: {maxPreparationSeconds: 1}},
      seed: 88,
    },
  });
  expect(response.ok()).toBeTruthy();
  const comparison = await response.json();
  expect(comparison.winner).toBeNull();
  for (const result of Object.values(comparison.strategies)) {
    expect(result.phases.part3_embarkation.status).toBe('not_started');
    expect(result.replay.aircraft_events).toEqual([]);
  }
});


test('phone layout has no document-level horizontal overflow', async ({page}) => {
  await page.goto('/');
  await expect(page.getByText('Ready · same passengers and one continuous clock')).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBe(dimensions.client);
});
