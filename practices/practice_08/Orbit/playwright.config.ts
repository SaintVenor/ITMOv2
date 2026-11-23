import { defineConfig } from '@playwright/test';

const baseURL = 'http://127.0.0.1:' + (process.env.ORBIT_TEST_WEB_PORT ?? '5188');

export default defineConfig({
  testDir: './frontend/tests',
  workers: 1,
  use: {
    baseURL,
    browserName: 'chromium',
    locale: 'ru-RU',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'node scripts/orbit.mjs dev',
    url: baseURL + '/api/health',
    timeout: 30_000,
    reuseExistingServer: false,
  },
});
