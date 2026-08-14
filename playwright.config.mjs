import {defineConfig, devices} from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'web-experience.spec.mjs',
  timeout: 120_000,
  expect: {timeout: 20_000},
  use: {
    baseURL: 'http://127.0.0.1:8765',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'python3 -m boarding_sim --port 8765',
    url: 'http://127.0.0.1:8765/api/config',
    reuseExistingServer: false,
    timeout: 30_000,
  },
  projects: [
    {name: 'chromium-desktop', use: {...devices['Desktop Chrome']}},
    {name: 'chromium-phone', use: {...devices['iPhone 13'], browserName: 'chromium', viewport: {width: 390, height: 844}}},
  ],
});
