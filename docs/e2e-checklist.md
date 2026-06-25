# End-to-End Smoke Test (S30)

The full MVP workflow: **upload → process → live voice interview → feedback**.
Legend: ✅ verified programmatically this build · 🧑‍💻 needs a real browser (mic + audio).

## Setup
```bash
# 1. Redis
redis-server --daemonize yes        # or: docker compose up -d
# 2. Ollama (model pulled once)
ollama serve &                      # ollama pull llama3.2
# 3. Backend
cd backend && cp .env.example .env && uv sync && uv run uvicorn app.main:app
# 4. Frontend
cd frontend && cp .env.example .env && npm install && npm run dev
```
Open `http://localhost:5173` in Chrome. **Use headphones.**

## Checklist

| # | Step | Expected | Status |
|---|------|----------|--------|
| 1 | Upload a PDF resume | status → `ready` (~10–20s) | ✅ (Phase 2) |
| 2 | Upload a DOCX resume | status → `ready` | ✅ (Phase 2) |
| 3 | Upload a `.txt` | rejected with 422 | ✅ (Phase 2) |
| 4 | Click **Start Interview** | lands in room, AI greeting plays | 🧑‍💻 (greeting verified server-side S21) |
| 5 | Speak an answer, then pause | your caption appears; AI responds with audio | 🧑‍💻 (loop verified server-side S21) |
| 6 | Continue a few turns | AI questions reference your resume | ✅ (RAG grounding, S21) |
| 7 | Captions show both sides | candidate right / AI left, auto-scroll | 🧑‍💻 |
| 8 | Click **End Interview** | navigates to feedback page | 🧑‍💻 |
| 9 | Feedback renders | overall score + 3 assessments + 3 lists | ✅ (S22) |
| 10 | **Start New Interview** | returns to upload, state reset | 🧑‍💻 |
| 11 | Kill backend mid-interview | "Reconnecting…" badge → resumes on restart | ✅ server resume (S28) · 🧑‍💻 browser badge |
| 12 | No CORS / console errors throughout | clean DevTools console | ✅ CORS (S23) · 🧑‍💻 console |

## Notes
- Items 4/5/7/8/10/12 (browser half) require manual verification — `getUserMedia`, AudioWorklet,
  and playback only run in a real browser; the underlying protocol + pipeline are proven server-side.
- The audio contract (16kHz mono int16 PCM ↔ WAV) was round-trip verified in Phase 3.
- Reconnect server logic proven by `backend/scripts/reconnect_test.py`; the browser auto-reconnect
  badge is the only reconnect piece needing a manual check.

## Run results — 2026-06-25 (programmatic pass)

Driven via curl + `scripts/interview_client.py` against a live backend (Ollama `llama3.2`,
faster-whisper `base.en`, macOS `say` TTS). All automatable items passed.

| # | Item | Result |
|---|------|--------|
| 1 | PDF upload | ✅ → `ready` |
| 2 | DOCX upload | ✅ → `ready` |
| 3 | `.txt` upload | ✅ HTTP 422 |
| 4 | AI greeting | ✅ greeted candidate by name, asked a resume-grounded first question |
| 5 | Spoken answer → AI response | ✅ STT transcribed; AI replied with streamed audio (376–610 KB/turn) |
| 6 | Resume-grounded questions | ✅ cited PyTorch vs TensorFlow, Kubernetes, 10M users, AWS, latency |
| 9 | Feedback report | ✅ overall 85 · comm 90 · tech 80 · resume_knowledge 95 · 2/2/2 lists |
| 11 | Reconnect/resume | ✅ drop→active (no premature feedback)→resume→graceful end→completed+feedback |
| 12 | CORS | ✅ preflight + origin enforcement |
| — | Frontend dev server | ✅ serves HTTP 200 at :5173 |
| — | Transcript persistence | ✅ 5 ordered turns; status `completed` |

**Pending manual (browser only):** 7 (caption DOM), 8 (End → route), 10 (Start New → reset),
11b ("Reconnecting…" badge). All ride protocols/flows already proven above.

## Browser verification

### A. Automated (Playwright) — items 7, 8, 9(UI), 10
A real headless Chromium with fake-media flags. Covers the DOM + routing flow (it cannot do a
real spoken turn — a fake mic is silent — so it ends the interview right after the greeting).

```bash
# with backend + redis + ollama + `npm run dev` all running:
cd frontend
npm install                    # pulls @playwright/test (now in devDependencies)
npx playwright install chromium
npm run test:e2e               # runs tests/browser_e2e.spec.js
```
Expected: upload → "Start Interview" enables → routes to /interview/:id → greeting caption
appears → End → /feedback/:id → "Overall Score" renders → Start New → back to upload. Green = 7/8/9/10 pass.

### B. Human-only — the real audio experience + #11b reconnect
A fake mic can't validate that you can *speak and be heard* or that the AI *sounds* natural.
Do this once, in Chrome, **with headphones**:
1. `npm run dev`, open http://localhost:5173, upload a resume, click **Start Interview**, grant mic.
2. **Hear** the AI greeting; the orb pulses while speaking, rings green when listening.
3. **Speak** an answer, then pause ~1s → your caption appears (right), AI follow-up plays (left).
4. Do 2–3 turns; confirm questions reference your resume.
5. **#11b reconnect:** mid-interview, stop the backend (Ctrl-C) → header shows "Reconnecting…";
   restart `uvicorn` within ~8s → it reconnects and the AI replays its last question.
6. **End Interview** → feedback report → **Start New Interview** → home.
7. Throughout: DevTools console clean (no CORS/errors).
