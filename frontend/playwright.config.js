import { defineConfig } from '@playwright/test'

// Browser E2E for the DOM/routing/reconnect items. Uses Chrome fake-media flags so
// getUserMedia/AudioWorklet succeed without real hardware. NOTE: a fake mic produces
// silence, so no real spoken turn happens — the actual listen/speak audio experience
// is still a human-only check (see docs/e2e-checklist.md).
export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: { timeout: 60_000 },
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    launchOptions: {
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--autoplay-policy=no-user-gesture-required',
      ],
    },
  },
})
