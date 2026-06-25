// Browser E2E — covers the checklist items that need a real browser DOM/routing.
//
// Prerequisites (run all three first, in separate terminals):
//   backend:  cd backend && uv run uvicorn app.main:app
//   redis:    redis-server --daemonize yes
//   ollama:   ollama serve
//   frontend: cd frontend && npm run dev
// Then:       cd frontend && npx playwright test
//
// Covers checklist #7 (captions render), #8 (End -> feedback route),
// #9 (feedback renders in browser), #10 (Start New -> reset).
// Does NOT cover a real spoken turn (fake mic = silence) or #11b reconnect badge
// (needs killing the backend mid-run) — those stay manual.

import { test, expect } from '@playwright/test'

const RESUME = process.env.RESUME_PATH || 'tests/fixtures/resume.pdf'

test('upload → interview room → end → feedback → start new', async ({ page }) => {
  // --- Upload screen ---
  await page.goto('/')
  await expect(page.getByText('AI Interview Simulator')).toBeVisible()

  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByText('Drag & drop your resume here').click(),
  ])
  await chooser.setFiles(RESUME)

  // Resume processing (extract → LLM structure → embed) can take ~10–30s.
  const startBtn = page.getByRole('button', { name: 'Start Interview' })
  await expect(startBtn).toBeVisible({ timeout: 60_000 })
  await startBtn.click()

  // --- Interview room: routed + captions (#7) ---
  await expect(page).toHaveURL(/\/interview\//)
  await expect(page.getByText('Transcript')).toBeVisible()
  // AI greeting bubble (left/grey) appears once the server greets.
  await expect(page.locator('span.bg-slate-700').first()).toBeVisible({ timeout: 60_000 })

  // --- End interview (#8) → feedback route ---
  await page.getByRole('button', { name: /End Interview/ }).click()
  await expect(page).toHaveURL(/\/feedback\//, { timeout: 30_000 })

  // --- Feedback renders (#9) ---
  await expect(page.getByText('Overall Score')).toBeVisible({ timeout: 60_000 })

  // --- Start New Interview (#10) → home + reset ---
  await page.getByRole('button', { name: 'Start New Interview' }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByText('Drag & drop your resume here')).toBeVisible()
})
