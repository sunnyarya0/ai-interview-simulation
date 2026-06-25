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
