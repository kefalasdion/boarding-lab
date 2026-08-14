// Record the public boarding race in capture mode for the LinkedIn video.
// The race is compressed to a fixed wall-clock length so the recording stays
// the same duration however long the corrected simulation runs.
import {chromium} from '@playwright/test';
import {rename} from 'node:fs/promises';
import {join} from 'node:path';

const baseURL = process.argv[2] ?? 'http://127.0.0.1:8791';
const outputDirectory = process.argv[3] ?? 'output';
const RACE_SECONDS = 34;
const RESULT_HOLD_MS = 6000;

const browser = await chromium.launch({headless: true});
try {
  const probeContext = await browser.newContext();
  const probe = await probeContext.newPage();
  await probe.goto(`${baseURL}/data/default-comparison.json`);
  const duration = await probe.evaluate(async (url) => {
    const artifact = await (await fetch(url)).json();
    const representative = artifact.representative;
    return Math.max(
      ...representative.strategy_order.map(
        (id) => representative.strategies[id].replay.ends_at_seconds,
      ),
    );
  }, `${baseURL}/data/default-comparison.json`);
  await probeContext.close();

  const speed = duration / RACE_SECONDS;
  console.log(
    JSON.stringify({simulated_seconds: duration, playback_speed: Number(speed.toFixed(3))}),
  );

  const context = await browser.newContext({
    viewport: {width: 1080, height: 1350},
    deviceScaleFactor: 1,
    recordVideo: {dir: outputDirectory, size: {width: 1080, height: 1350}},
  });
  const page = await context.newPage();
  await page.goto(`${baseURL}/?capture=1&autoplay=1&speed=${speed}`);
  await page.waitForFunction(
    () => document.getElementById('race-status')?.textContent?.startsWith('Ready'),
    null,
    {timeout: 120_000},
  );
  await page.waitForFunction(
    (target) => Number(document.getElementById('timeline-scrubber').value) >= target,
    Math.floor(duration) - 1,
    {timeout: (RACE_SECONDS + 60) * 1000},
  );

  await page.evaluate(() => {
    document.body.dataset.captureStage = 'result';
  });
  await page.waitForTimeout(RESULT_HOLD_MS);
  await page.screenshot({path: join(outputDirectory, 'poster.png')});

  const video = page.video();
  await context.close();
  await rename(await video.path(), join(outputDirectory, 'race.webm'));
  console.log('recorded race.webm and poster.png');
} finally {
  await browser.close();
}
