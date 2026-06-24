# AI Interview Simulator — Sprint Plan

> **How to use this plan**
> Each sprint is a single, deployable slice of working software. Every sprint has:
> - **Goal** — the one sentence that describes what you're building.
> - **Tasks** — the exact files/functions to create.
> - **Done when** — the concrete test that proves it works.
> - **Depends on** — what must be complete before this sprint starts.
>
> Sprints are intentionally tiny (~half-day to 1 day each). Do not skip ahead.
> Reference: `docs/architecture.md` for all design decisions.

---

## Phase 1 — Foundation & Scaffolding

### S01 · Backend skeleton

**Goal:** A FastAPI app that starts, has a health check, and loads config from `.env`.

**Tasks**
- Create `backend/` directory with `pyproject.toml` (or `requirements.txt`)
- Install: `fastapi`, `uvicorn[standard]`, `python-dotenv`, `pydantic-settings`
- `backend/app/main.py` — FastAPI app, `GET /health` returns `{"status": "ok"}`
- `backend/app/core/config.py` — `Settings` class with `DATABASE_URL`, `REDIS_URL`, `UPLOAD_DIR`, `OLLAMA_BASE_URL`
- `backend/.env.example`

**Done when:** `uvicorn app.main:app --reload` starts and `curl localhost:8000/health` returns `{"status":"ok"}`.

**Depends on:** nothing.

---

### S02 · Database models + migrations

**Goal:** SQLAlchemy models for all four tables; database file created on startup.

**Tasks**
- Install: `sqlalchemy`, `aiosqlite`, `alembic`
- `backend/app/db/models.py` — `Resume`, `Interview`, `TranscriptTurn`, `Feedback` (schema from architecture §7.1)
- `backend/app/db/session.py` — async engine + `get_db` dependency
- `backend/app/db/base.py` — `Base = declarative_base()`
- Run `alembic init` + write `env.py` + generate first migration
- On startup, apply migrations (`alembic upgrade head`)

**Done when:** `python -c "from app.db.models import Resume; print('ok')"` passes; `interview.db` file is created with all four tables visible via `sqlite3 interview.db .tables`.

**Depends on:** S01.

---

### S03 · Redis + Docker Compose

**Goal:** Redis running locally; the app can ping it.

**Tasks**
- `docker-compose.yml` with a single `redis:7-alpine` service, port `6379`
- Install: `redis[asyncio]`
- `backend/app/cache/client.py` — async Redis client, `get_redis()` dependency, `ping()` helper
- Add `GET /health` check to also ping Redis

**Done when:** `docker compose up -d` starts Redis; `GET /health` returns `{"status":"ok","redis":"ok"}`.

**Depends on:** S01.

---

### S04 · Frontend skeleton

**Goal:** Vue 3 + Vite + Tailwind + Vue Router + Pinia scaffold with three empty route pages.

**Tasks**
- `cd frontend && npm create vite@latest . -- --template vue`
- Install: `vue-router`, `pinia`, `tailwindcss`, `@tailwindcss/vite`
- Configure Tailwind in `vite.config.js`
- `src/router/index.js` — three routes: `/` → `UploadView`, `/interview/:id` → `InterviewRoomView`, `/feedback/:id` → `FeedbackView`
- `src/views/UploadView.vue`, `InterviewRoomView.vue`, `FeedbackView.vue` — each just renders its name as an `<h1>`
- `src/stores/interviewStore.js` — empty Pinia store with `interviewId`, `resumeId`, `status` state
- `src/stores/mediaStore.js` — empty Pinia store with `isMicActive`, `isAiSpeaking` state

**Done when:** `npm run dev` starts; browser shows "UploadView" at `/`, "InterviewRoomView" at `/interview/test`, "FeedbackView" at `/feedback/test`.

**Depends on:** nothing.

---

### S05 · Frontend service layer stubs

**Goal:** Three service modules (HTTP, WebSocket, audio) that export real interfaces but are not yet implemented.

**Tasks**
- `src/services/httpClient.js` — `uploadResume(file)`, `getResumeStatus(id)`, `createInterview(resumeId)`, `getFeedback(interviewId)` — each throws `"not implemented"` for now
- `src/services/wsClient.js` — `connect(interviewId)`, `disconnect()`, `sendAudioFrame(buffer)`, `on(event, handler)` — stubs
- `src/services/audioEngine.js` — `startCapture()`, `stopCapture()`, `playAudioChunk(buffer)` — stubs

**Done when:** `import { uploadResume } from '@/services/httpClient'` works in the browser console without an error (it will throw "not implemented" when called — that is correct).

**Depends on:** S04.

---

## Phase 2 — Resume Upload & Processing

### S06 · Resume upload API

**Goal:** `POST /resumes` accepts a PDF or DOCX file, saves it to disk, creates a DB record, and returns a `resume_id`.

**Tasks**
- Install: `python-multipart`, `aiofiles`
- `backend/app/api/resumes.py` — router with `POST /resumes`
  - validate content-type (PDF / DOCX only; reject others with 422)
  - save file to `UPLOAD_DIR/{uuid4}.{ext}`
  - insert `Resume` row with `status="uploaded"`
  - return `{"resume_id": "...", "status": "uploaded"}`
- `GET /resumes/{id}/status` — return `{"resume_id": "...", "status": "..."}` (or 404)
- Register router in `main.py`

**Done when:**
```bash
curl -F "file=@resume.pdf" http://localhost:8000/resumes
# → {"resume_id": "abc123", "status": "uploaded"}
curl http://localhost:8000/resumes/abc123/status
# → {"resume_id": "abc123", "status": "uploaded"}
```

**Depends on:** S02.

---

### S07 · Text extraction from PDF and DOCX

**Goal:** Given a saved resume file, extract clean plain text.

**Tasks**
- Install: `pymupdf` (for PDF), `python-docx` (for DOCX)
- `backend/app/pipeline/extractor.py`
  - `extract_text(file_path: str) -> str`
  - branch on extension: `.pdf` → PyMuPDF, `.docx` → python-docx
  - strip boilerplate whitespace; return clean string
- Write a standalone test: `python -m app.pipeline.extractor path/to/resume.pdf` prints the text

**Done when:** Running the test against a real PDF and a real DOCX prints readable text with no crashes.

**Depends on:** S06.

---

### S08 · LLM adapter (Ollama)

**Goal:** A Python adapter that sends a prompt to Ollama and returns a streaming or complete response.

**Tasks**
- Install: `httpx`
- Make sure Ollama is running locally (`ollama pull qwen2.5:3b` or `llama3.2:3b`)
- `backend/app/pipeline/llm.py`
  - `class LLMAdapter` with `base_url` from config
  - `async def complete(prompt: str, system: str = "", temperature: float = 0.7) -> str`
  - `async def stream(prompt: str, system: str = "") -> AsyncIterator[str]` (yields token strings)
  - Both use Ollama's `/api/generate` or `/api/chat` endpoint
- Write a quick smoke test: call `complete("Say hello in one sentence.")` and print the result

**Done when:** Smoke test prints a sentence from the model. No crashes. Streaming test prints tokens one by one.

**Depends on:** S01.

---

### S09 · LLM-based resume structuring

**Goal:** Given extracted resume text, use the LLM to output a structured JSON profile.

**Tasks**
- `backend/app/pipeline/structurer.py`
  - `async def structure_resume(raw_text: str) -> dict` 
  - Sends a prompt asking the LLM to extract: `name`, `skills`, `experience` (list), `education` (list), `projects` (list), `technologies` (list)
  - System prompt instructs: output **only** valid JSON, no commentary
  - Parse the JSON response; raise `ValueError` if unparseable
  - Return the dict
- Smoke test: pipe a real resume text through and `print(json.dumps(result, indent=2))`

**Done when:** Smoke test prints a valid JSON object with the six fields populated. Edge case: test with a minimal one-paragraph "resume" — should still return valid JSON (fields may be empty lists).

**Depends on:** S07, S08.

---

### S10 · Embeddings adapter + Chroma setup

**Goal:** Embed text with sentence-transformers and store/query chunks in Chroma.

**Tasks**
- Install: `sentence-transformers`, `chromadb`
- `backend/app/pipeline/embeddings.py`
  - `class EmbeddingAdapter` — loads `all-MiniLM-L6-v2` on init
  - `def embed(texts: list[str]) -> list[list[float]]`
- `backend/app/db/chroma.py`
  - `get_chroma_client()` — returns a persistent Chroma client at `./chroma_db`
  - `get_or_create_collection(name: str)` helper
- Smoke test: embed `["Python developer", "Java developer"]`, assert the cosine distance between them is less than between `"Python developer"` and `"Football player"`

**Done when:** Smoke test assertions pass.

**Depends on:** S01.

---

### S11 · Resume chunking + indexing into Chroma

**Goal:** Split the structured profile into chunks and store them in Chroma, keyed by `resume_id`.

**Tasks**
- `backend/app/pipeline/indexer.py`
  - `def chunk_resume(structured: dict, resume_id: str) -> list[dict]`
    - one chunk per experience entry, per project, per skill group
    - each chunk: `{"text": "...", "metadata": {"resume_id": "...", "section": "experience|project|skills", ...}}`
  - `async def index_resume(resume_id: str, structured: dict) -> None`
    - chunk → embed → upsert into Chroma collection `"resumes"`
- Smoke test: index a fake structured profile; then query Chroma with `"machine learning experience"` and assert the top result is the relevant chunk

**Done when:** Smoke test returns the right chunk as the top result.

**Depends on:** S09, S10.

---

### S12 · Background worker setup (arq + Redis)

**Goal:** arq worker process running; a simple test job enqueues and executes.

**Tasks**
- Install: `arq`
- `backend/app/workers/worker.py`
  - `WorkerSettings` class — Redis DSN from config, list of functions: `[process_resume, generate_feedback]`
  - `async def process_resume(ctx, resume_id: str) -> None` — stub that just logs `f"processing {resume_id}"`
  - `async def generate_feedback(ctx, interview_id: str) -> None` — stub that just logs
- `backend/app/cache/queue.py` — `async def enqueue(pool, func_name, *args)` helper
- Update `POST /resumes` to enqueue `process_resume` after saving the file
- Run worker: `arq app.workers.worker.WorkerSettings`

**Done when:** Upload a resume → worker terminal logs `"processing <id>"` within 1 second.

**Depends on:** S03, S06.

---

### S13 · Resume processing job (full implementation)

**Goal:** Replace the stub with the real pipeline: extract → structure → index → update DB status.

**Tasks**
- `backend/app/workers/worker.py` — implement `process_resume`:
  1. load `Resume` from DB by `resume_id`
  2. `extract_text(resume.file_path)`
  3. `structure_resume(raw_text)` → save `structured_profile` to `Resume` row
  4. `index_resume(resume_id, structured)` → store in Chroma
  5. update `Resume.status = "ready"` (or `"failed"` on exception)
- Wire up proper DB session inside the worker context

**Done when:**
1. Upload a real PDF.
2. Poll `/resumes/{id}/status` — it transitions from `"uploaded"` → `"processing"` → `"ready"` (within ~10–20 s depending on hardware).
3. Query Chroma manually: collection `"resumes"` has documents for that `resume_id`.

**Depends on:** S09, S11, S12.

---

## Phase 3 — AI Adapters (STT, TTS, RAG)

### S14 · STT adapter (faster-whisper)

**Goal:** Given a bytes buffer of 16 kHz PCM audio, return a transcript string.

**Tasks**
- Install: `faster-whisper`
- `backend/app/pipeline/stt.py`
  - `class STTAdapter` — loads `WhisperModel("base", device="auto", compute_type="int8")` on init
  - `def transcribe(audio_bytes: bytes, sample_rate: int = 16000) -> str`
    - write bytes to a `tempfile`, run `model.transcribe(path, language="en")`, concatenate segments
  - `def transcribe_with_vad(audio_bytes: bytes) -> tuple[str, bool]`
    - returns `(text, is_speech)` — `is_speech=False` if Whisper returns empty/noise
- Smoke test: record a 3-second WAV file, call `transcribe()`, assert the output contains your spoken words

**Done when:** Smoke test output matches what you said (approximately).

**Depends on:** S01.

---

### S15 · TTS adapter (Piper)

**Goal:** Given a text string, return a bytes buffer of synthesized WAV audio.

**Tasks**
- Install Piper binary for your OS; download a voice model (e.g., `en_US-lessac-medium`)
- `backend/app/pipeline/tts.py`
  - `class TTSAdapter` — holds path to Piper binary + voice model
  - `def synthesize(text: str) -> bytes` — shell-out to Piper, capture stdout as WAV bytes
  - `async def synthesize_stream(text: str) -> AsyncIterator[bytes]`
    - split text by sentence (`. `, `? `, `! `)
    - yield audio bytes per sentence (so first audio arrives before full text is done)
- Smoke test: `synthesize("Hello, I am your AI interviewer.")` writes output to `test.wav`; play it and verify it sounds correct

**Done when:** `test.wav` plays back intelligibly.

**Depends on:** S01.

---

### S16 · RAG retriever

**Goal:** Given a query string and a `resume_id`, return the top-3 most relevant resume chunks as a formatted context block.

**Tasks**
- `backend/app/pipeline/retriever.py`
  - `class Retriever`
  - `async def retrieve(query: str, resume_id: str, top_k: int = 3) -> str`
    - embed query
    - query Chroma collection `"resumes"` with `where={"resume_id": resume_id}`
    - format results as a single string block ready to paste into a prompt
- Smoke test (requires a resume already indexed via S13):
  - `retrieve("Tell me about your Python experience", resume_id="...")` 
  - print result; verify it contains the relevant experience chunk

**Done when:** The printed context block contains the expected resume section and is under ~500 tokens.

**Depends on:** S10, S11.

---

## Phase 4 — Interview API & Orchestrator

### S17 · Interview create endpoint

**Goal:** `POST /interviews` creates an interview record linked to a ready resume and returns an `interview_id`.

**Tasks**
- `backend/app/api/interviews.py` — router
  - `POST /interviews` body: `{"resume_id": "..."}`
    - verify `Resume` exists and `status == "ready"` (raise 400 otherwise)
    - create `Interview` row with `status="created"`
    - return `{"interview_id": "...", "status": "created"}`
  - `GET /interviews/{id}` — return interview row as JSON
- Register router in `main.py`

**Done when:**
```bash
curl -X POST http://localhost:8000/interviews -H "Content-Type: application/json" \
  -d '{"resume_id":"abc123"}'
# → {"interview_id": "xyz789", "status": "created"}
```
Posting with a non-ready or nonexistent `resume_id` returns a 400.

**Depends on:** S02, S06.

---

### S18 · Prompt builder

**Goal:** A function that assembles the full LLM prompt for one conversation turn.

**Tasks**
- `backend/app/orchestrator/prompt.py`
  - `def build_system_prompt(structured_profile: dict) -> str`
    - role: professional technical interviewer
    - rules: one question at a time, be conversational, use candidate's actual experience, ask follow-ups, end naturally
    - compact profile summary embedded in the system prompt
  - `def build_turn_prompt(history: list[dict], rag_context: str, last_answer: str) -> str`
    - history format: `[{"role": "assistant"|"user", "content": "..."}]`
    - inserts RAG context before the latest answer
    - keeps last N=10 turns; if `len(history) > 10` it prepends a one-line summary stub (hardcoded for now)
- Unit test (no LLM needed): call `build_turn_prompt` with fake data; assert the output string contains the RAG context and last answer

**Done when:** Unit test passes; prompt string prints cleanly.

**Depends on:** S09.

---

### S19 · Interview Orchestrator — state machine (skeleton)

**Goal:** An `InterviewOrchestrator` class that holds state, transitions correctly, and stores state in Redis.

**Tasks**
- `backend/app/orchestrator/state.py`
  - `InterviewState` Enum: `GREETING, ASK_QUESTION, LISTENING, TRANSCRIBING, DECIDING, FOLLOW_UP, CLOSING, DONE`
- `backend/app/orchestrator/orchestrator.py`
  - `class InterviewOrchestrator`
  - `__init__(self, interview_id, resume_id, redis, db)`
  - `async def load_state()` — read state from Redis (key: `interview:{id}:state`)
  - `async def save_state()` — write state to Redis
  - `async def transition(new_state: InterviewState)` — validates transition, saves
  - `async def append_turn(speaker: str, text: str)` — push to Redis list `interview:{id}:history`
  - `async def get_history() -> list[dict]` — read from Redis
  - Stub methods (raise `NotImplementedError`): `handle_audio_frame()`, `run_greeting()`, `run_asking()`, `run_deciding()`
- Unit test: instantiate with a mock Redis; call `transition(GREETING)` → `transition(ASK_QUESTION)` → assert state is `ASK_QUESTION`. Assert invalid transition (e.g., `GREETING` → `DONE`) raises `ValueError`.

**Done when:** Unit test passes.

**Depends on:** S03, S17.

---

### S20 · WebSocket gateway (connection handling)

**Goal:** `WS /interviews/{id}/stream` accepts a connection, initializes the orchestrator, and handles disconnects cleanly.

**Tasks**
- `backend/app/ws/gateway.py`
  - `@app.websocket("/interviews/{interview_id}/stream")`
  - on connect: verify `interview_id` exists in DB; update status to `"active"`; instantiate `InterviewOrchestrator`; run `orchestrator.run_greeting()` (stub — just sends a JSON message `{"type":"greeting","text":"Hello!"}`)
  - main loop: `await websocket.receive()` — if binary, call `orchestrator.handle_audio_frame(data)`; if JSON, handle control messages
  - on disconnect: update interview status to `"completed"`; enqueue `generate_feedback` job
- Test: open a WebSocket connection via browser console or `wscat`; verify a greeting message arrives; disconnect; verify interview status becomes `"completed"` in DB

**Done when:** `wscat -c ws://localhost:8000/interviews/xyz789/stream` receives `{"type":"greeting","text":"Hello!"}`.

**Depends on:** S17, S19, S12.

---

### S21 · Full conversation turn (STT → RAG → LLM → TTS)

**Goal:** Implement `handle_audio_frame` so one complete question-answer-response cycle works end-to-end.

**Tasks**
- `backend/app/orchestrator/orchestrator.py` — implement the real loop:
  1. `handle_audio_frame(audio_bytes)`:
     - accumulate bytes in a Redis buffer `interview:{id}:audio_buf`
     - when VAD detects end-of-utterance (use `STTAdapter.transcribe_with_vad`), flush the buffer
  2. on final transcript:
     - `append_turn("candidate", transcript_text)`
     - send `{"type":"transcript","speaker":"candidate","text":"..."}` to client
     - call `RAGRetriever.retrieve(transcript_text, resume_id)`
     - call `PromptBuilder.build_turn_prompt(history, rag_context, transcript_text)`
     - stream `LLMAdapter.stream(prompt, system_prompt)`:
       - accumulate tokens until sentence boundary
       - at each sentence: call `TTSAdapter.synthesize(sentence)` → send binary audio chunk over WS
       - also send `{"type":"transcript","speaker":"ai","text":"..."}` per sentence
     - after streaming completes: `append_turn("ai", full_response)`, `transition(DECIDING)`
  3. `run_deciding()`:
     - count turns; if ≥ configured max (e.g., 6 QA pairs) → `transition(CLOSING)` and send closing message
     - otherwise → `transition(ASK_QUESTION)` (cycle repeats)
- Integration test (manual): connect via `wscat`, send a real 3-second audio clip as binary, verify you receive back a transcript message + audio bytes + AI transcript within ~3 seconds

**Done when:** Manual integration test produces audible AI response to a spoken input.

**Depends on:** S14, S15, S16, S18, S19, S20.

---

### S22 · Feedback generation job (full implementation)

**Goal:** After the interview ends, generate and store a structured feedback report.

**Tasks**
- `backend/app/workers/worker.py` — implement `generate_feedback`:
  1. load `Interview` + all `TranscriptTurn` rows
  2. load `Resume.structured_profile`
  3. call `LLMAdapter.complete(feedback_prompt)` where the prompt includes the full transcript and asks for JSON output with: `overall_score`, `communication`, `technical`, `resume_knowledge`, `strengths`, `weaknesses`, `improvements`
  4. parse the JSON; create `Feedback` row in DB
  5. update `Interview.status = "completed"`
- `backend/app/api/interviews.py` — add `GET /interviews/{id}/feedback`
  - return 404 if not yet generated, 200 with the feedback JSON when ready
- `backend/app/orchestrator/prompt.py` — add `build_feedback_prompt(transcript_turns, structured_profile) -> str`
- Smoke test: manually trigger the job for a completed interview; verify `GET /interviews/{id}/feedback` returns all seven fields

**Done when:** After a complete interview session (even a simulated one), the feedback endpoint returns a JSON report with all seven fields populated.

**Depends on:** S08, S20.

---

## Phase 5 — Frontend Implementation

### S23 · Upload View (real implementation)

**Goal:** Drag-and-drop file upload, progress polling, and navigation to the interview room.

**Tasks**
- `src/services/httpClient.js` — implement `uploadResume(file)` and `getResumeStatus(id)` using `fetch`
- `src/views/UploadView.vue`:
  - drag-and-drop zone (Tailwind-styled)
  - file picker fallback
  - on file select: call `uploadResume` → store `resume_id` in `interviewStore`
  - poll `getResumeStatus` every 2 seconds; show spinner + `"Processing your resume…"` while `status !== "ready"`
  - when `status === "ready"`: enable `"Start Interview"` button
  - on button click: call `createInterview(resumeId)` → store `interview_id` → `router.push('/interview/:id')`
- `src/stores/interviewStore.js` — add `resumeId`, `interviewId`, `resumeStatus` state + actions

**Done when:** Upload a real PDF in the browser; the button enables after ~10–30 s; clicking it navigates to `/interview/:id`.

**Depends on:** S05, S06, S13, S17.

---

### S24 · Audio engine (real implementation)

**Goal:** `getUserMedia` → AudioWorklet → 16 kHz PCM frames → WebSocket, with client-side VAD.

**Tasks**
- `public/audio-processor.js` (AudioWorklet):
  - receives raw PCM from the browser (usually 44.1 kHz or 48 kHz float32)
  - downsamples to 16 kHz mono int16
  - emits 20 ms frames via `port.postMessage`
- `src/services/audioEngine.js` — implement:
  - `startCapture()`: `getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })`
  - create `AudioContext` at 48000 Hz; create `AudioWorkletNode` loading `audio-processor.js`
  - on each frame: run simple energy VAD (RMS > threshold → speech)
  - while VAD active: call `wsClient.sendAudioFrame(int16Buffer)`
  - on silence > 800 ms: send `{"type":"end_of_utterance"}` JSON message
  - `stopCapture()`: stop tracks + close context
  - `playAudioChunk(wavBytes)`: decode + enqueue into a `AudioBufferSourceNode` playback queue

**Done when:** Open InterviewRoomView in the browser (before the WS is wired), call `audioEngine.startCapture()` from the console, speak for 2 seconds then stop; verify `console.log` shows VAD triggering and frames being buffered.

**Depends on:** S05.

---

### S25 · Interview Room View

**Goal:** The live "meeting room" screen — connects WebSocket, sends audio, plays AI speech, shows captions.

**Tasks**
- `src/services/wsClient.js` — implement:
  - `connect(interviewId)`: open `WebSocket(ws://localhost:8000/interviews/{id}/stream)`
  - route incoming messages by `type`: `greeting` | `transcript` | binary audio
  - `sendAudioFrame(buffer)`: send binary
  - `on(event, handler)` for `transcript`, `ai_speaking`, `error`
- `src/views/InterviewRoomView.vue`:
  - on mount: `wsClient.connect(interviewId)` + `audioEngine.startCapture()`
  - show AI waveform / animated ring when `mediaStore.isAiSpeaking`
  - scrolling transcript panel: candidate text (right-aligned) + AI text (left-aligned)
  - on incoming binary: `audioEngine.playAudioChunk(data)`
  - on incoming `transcript`: append to transcript list; set `isAiSpeaking` flag
  - mic mute button: `audioEngine.stopCapture()` / `startCapture()`
  - "End Interview" button: send `{"type":"end_interview"}` → `wsClient.disconnect()` → `router.push('/feedback/:id')`
  - barge-in: if VAD fires while `isAiSpeaking`, call `audioEngine.pausePlayback()` and resume listening

**Done when:** Full manual end-to-end: upload PDF → Start Interview → speak a sentence → hear the AI respond → see captions for both sides → click End → navigate to feedback.

**Depends on:** S21, S23, S24.

---

### S26 · Feedback View

**Goal:** Display the complete feedback report after the interview.

**Tasks**
- `src/services/httpClient.js` — implement `getFeedback(interviewId)` — polls every 2 s until `feedback` is not null
- `src/views/FeedbackView.vue`:
  - on mount: poll `getFeedback` (show spinner while generating)
  - once ready, render:
    - **Overall Score** — large number / ring chart (CSS only, no lib needed)
    - **Communication** — text block
    - **Technical Assessment** — text block
    - **Resume Knowledge** — text block
    - **Strengths** — bullet list
    - **Weaknesses** — bullet list
    - **Suggested Improvements** — bullet list
  - "Start a New Interview" button → `router.push('/')`

**Done when:** After completing an interview, the feedback page loads and shows all seven sections with real content from the LLM.

**Depends on:** S22, S25.

---

## Phase 6 — Integration & Hardening

### S27 · Transcript persistence

**Goal:** Every AI and candidate turn is saved to `TranscriptTurn` in SQLite during the interview (not just at the end).

**Tasks**
- `backend/app/orchestrator/orchestrator.py` — in `append_turn`:
  - in addition to Redis: insert a `TranscriptTurn` row asynchronously
- Verify: after a complete interview session, `SELECT * FROM transcript_turn WHERE interview_id = '...'` shows all turns in order

**Done when:** `sqlite3 interview.db "SELECT speaker, text FROM transcript_turn ORDER BY turn_index"` prints the full dialogue.

**Depends on:** S21.

---

### S28 · WebSocket error handling + auto-reconnect

**Goal:** The browser reconnects if the WebSocket drops; the server resumes the existing interview.

**Tasks**
- `src/services/wsClient.js`:
  - on `close` event: if `interview.status !== "completed"`, retry after 2 s (max 5 retries)
  - send a `{"type":"resume","interview_id":"..."}` message on reconnect
- `backend/app/ws/gateway.py`:
  - on `resume` message: reload state from Redis; re-send last AI message from history
- `src/views/InterviewRoomView.vue`:
  - show a "Reconnecting…" badge during retry
  - hide it when `wsClient` emits `connected` again

**Done when:** Kill and restart the backend mid-interview; the browser shows "Reconnecting…" then "connected" within ~5 s; the interview continues.

**Depends on:** S25.

---

### S29 · Config & environment cleanup

**Goal:** All hardcoded values moved to config; a working `.env.example`.

**Tasks**
- `backend/app/core/config.py` — add: `OLLAMA_MODEL`, `WHISPER_MODEL`, `PIPER_VOICE`, `MAX_INTERVIEW_TURNS`, `CHROMA_PATH`, `UPLOAD_DIR`
- Replace every hardcoded string in pipeline adapters with config values
- `frontend/src/config.js` (or `.env`) — `VITE_API_BASE_URL`, `VITE_WS_BASE_URL`
- `backend/.env.example` and `frontend/.env.example` — document every variable
- `README.md` — quick start: install deps, copy env, `docker compose up`, `uvicorn`, `npm run dev`

**Done when:** A fresh clone with only `.env` files filled in produces a working system.

**Depends on:** all previous sprints.

---

### S30 · End-to-end smoke test (manual checklist)

**Goal:** Walk through the complete MVP workflow without errors and document any remaining issues.

**Checklist (must all pass)**
- [ ] Upload a PDF resume → status transitions to `ready`
- [ ] Upload a DOCX resume → same
- [ ] Upload a non-supported file type → 422 error shown in UI
- [ ] Start interview → greeting audio plays
- [ ] Speak an answer → AI responds within ~3 seconds
- [ ] AI asks a follow-up → verify it references the actual resume
- [ ] Click "End Interview" → navigate to feedback
- [ ] Feedback page shows all 7 sections with non-empty content
- [ ] "Start a New Interview" returns to Upload
- [ ] Kill backend mid-interview → reconnect works
- [ ] No browser console errors throughout

**Done when:** All 11 checklist items pass on the target demo machine.

**Depends on:** all previous sprints.

---

## Sprint Summary

| # | Sprint | Phase | Deliverable |
|---|--------|-------|------------|
| S01 | Backend skeleton | Foundation | FastAPI + health check |
| S02 | DB models | Foundation | SQLite + 4 tables |
| S03 | Redis + Docker | Foundation | Redis running, ping OK |
| S04 | Frontend skeleton | Foundation | Vue + Router + Tailwind + 3 routes |
| S05 | FE service stubs | Foundation | 3 service module interfaces |
| S06 | Resume upload API | Resume | POST/GET /resumes |
| S07 | Text extraction | Resume | PDF + DOCX → plain text |
| S08 | LLM adapter | Resume | Ollama complete + stream |
| S09 | Resume structuring | Resume | LLM → JSON profile |
| S10 | Embeddings + Chroma | Resume | Embed + store + query |
| S11 | Resume indexing | Resume | Chunked vectors in Chroma |
| S12 | Worker setup | Resume | arq + Redis queue running |
| S13 | Resume job | Resume | Full pipeline, status=ready |
| S14 | STT adapter | AI | faster-whisper transcription |
| S15 | TTS adapter | AI | Piper sentence audio |
| S16 | RAG retriever | AI | Top-k context from Chroma |
| S17 | Interview create API | Orchestrator | POST /interviews |
| S18 | Prompt builder | Orchestrator | System + turn prompts |
| S19 | Orchestrator skeleton | Orchestrator | State machine + Redis state |
| S20 | WS gateway | Orchestrator | Connect/disconnect + greeting |
| S21 | Full conversation turn | Orchestrator | STT→RAG→LLM→TTS loop |
| S22 | Feedback job | Orchestrator | Report generated + stored |
| S23 | Upload View | Frontend | Real upload + polling + start |
| S24 | Audio engine | Frontend | Capture + VAD + playback |
| S25 | Interview Room View | Frontend | Live meeting UI |
| S26 | Feedback View | Frontend | Report display |
| S27 | Transcript persistence | Hardening | All turns in SQLite |
| S28 | WS reconnect | Hardening | Auto-reconnect mid-interview |
| S29 | Config cleanup | Hardening | All values in .env |
| S30 | E2E smoke test | Hardening | Full checklist passes |

**Total: 30 sprints across 6 phases.**

---

## Dependency Graph

```
S01 ──┬──► S02 ──► S06 ──► S07 ──► S09 ──► S11 ──► S13
      │           │                │
      │           └──► S17         └──► S08 (LLM) ──► S22
      │
      ├──► S03 ──► S12 ──► S13
      │    │       │
      │    └───────┴──► S19 ──► S20 ──► S21 ──► S25
      │                                  │
S04 ──┴──► S05 ──► S23 ──────────────────┘
                   │
                   └──► S24 ──► S25 ──► S26

S10 ──► S11 ──► S13
S14 ──► S21
S15 ──► S21
S16 ──► S21
S18 ──► S21
```

**Critical path (must not be parallelized):**
`S01 → S02 → S06 → S07 → S08 → S09 → S11 → S13 → S17 → S19 → S20 → S21 → S25 → S30`

**Safe to parallelize:**
- S03 (Redis) alongside S02 (DB models)
- S04 + S05 (Frontend scaffold) alongside the entire backend Phase 2
- S14 (STT), S15 (TTS), S16 (RAG) can all be built in parallel once S10 is done
- S23 (Upload View) alongside S14–S16
