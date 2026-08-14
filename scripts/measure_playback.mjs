import {chromium} from '@playwright/test';

const baseURL = process.argv[2] ?? 'http://127.0.0.1:8765';
const browser = await chromium.launch({headless: true});
try {
  const page = await browser.newPage({viewport: {width: 1440, height: 900}});
  await page.goto(baseURL);
  await page.getByText('Ready · same passengers and one continuous clock', {exact: true}).waitFor();
  await page.getByLabel('Speed').selectOption('4');
  await page.getByRole('button', {name: 'Play', exact: true}).click();
  const result = await page.evaluate(() => new Promise((resolve) => {
    const intervals = [];
    let start = null;
    let previous = null;
    const sample = (now) => {
      if (start === null) {
        start = now;
        previous = now;
      } else {
        intervals.push(now - previous);
        previous = now;
      }
      if (now - start >= 30_000) {
        const sorted = intervals.slice(2).sort((a, b) => a - b);
        const pick = (fraction) => sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * fraction))];
        resolve({
          sampled_frames: sorted.length,
          median_ms: pick(0.5),
          p95_ms: pick(0.95),
          maximum_ms: sorted.at(-1),
        });
        return;
      }
      requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  }));
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
