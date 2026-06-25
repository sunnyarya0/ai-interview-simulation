# AI Interview Simulator

An AI-powered interview platform where a candidate uploads their resume, joins a real-time voice conversation with an AI interviewer, and receives detailed feedback — all running locally with open-source models.

---

## What it does

1. **Upload a resume** (PDF or DOCX) — the AI extracts and indexes your experience
2. **Start an interview** — join a live voice session with an AI interviewer
3. **Talk naturally** — the AI asks questions, listens, and follows up based on your resume
4. **Get feedback** — receive a structured report covering technical skills, communication, and more

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, Vite, Tailwind CSS, Pinia, Vue Router |
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Database | SQLite (metadata), Chroma (resume vectors) |
| Cache / Queue | Redis, arq |
| LLM | Ollama (Qwen, Llama, Phi — local) |
| STT | faster-whisper |
| TTS | Piper |
| Embeddings | sentence-transformers |

Everything runs locally. No cloud APIs, no usage costs.

---

## Prerequisites

- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Ollama](https://ollama.com) — local LLM server
- Redis — via Docker (`docker compose up -d`) or Homebrew (`brew install redis`)

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/sunnyarya0/ai-interview-simulation.git
cd ai-interview-simulation
```

### 2. Backend

```bash
cd backend
cp .env.example .env        # edit if needed
uv sync
uv run uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`. Migrations run automatically on startup.

### 3. Frontend

```bash
cd frontend
cp .env.example .env      # optional — defaults point at localhost:8000
npm install
npm run dev
```

The app opens at `http://localhost:5173`. **Use headphones** for the interview — the AI's
voice and your mic share the listening window (barge-in is not enabled in V1), so headphones
prevent the AI from hearing itself.

### 4. Redis

```bash
# Docker
docker compose up -d

# or Homebrew
redis-server --daemonize yes
```

### 5. Ollama

```bash
ollama serve
ollama pull qwen2.5:3b      # or llama3.2:3b or phi3:mini
```

---

## Environment variables

Copy `backend/.env.example` to `backend/.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./interview.db` | SQLite file path |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `UPLOAD_DIR` | `./uploads` | Where resume files are saved |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## Project structure

```
ai-interview-simulation/
├── backend/
│   ├── app/
│   │   ├── api/            # REST routers (resume, interview)
│   │   ├── cache/          # Redis client
│   │   ├── core/           # Config, logger
│   │   ├── db/             # SQLAlchemy models, session
│   │   ├── orchestrator/   # Interview state machine
│   │   ├── pipeline/       # STT, TTS, LLM, embeddings, RAG
│   │   ├── workers/        # arq background jobs
│   │   └── main.py
│   ├── alembic/            # DB migrations
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── views/          # UploadView, InterviewRoomView, FeedbackView
│       ├── stores/         # Pinia state
│       ├── services/       # HTTP, WebSocket, audio engine
│       └── router/
├── docs/
│   ├── project-overview.md
│   ├── architecture.md     # Full system design with ADRs
│   └── sprint-plan.md      # 30-sprint implementation plan
└── docker-compose.yml
```

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (DB + Redis status) |
| `POST` | `/resumes` | Upload a resume |
| `GET` | `/resumes/{id}/status` | Poll processing status |
| `POST` | `/interviews` | Start an interview |
| `WS` | `/interviews/{id}/stream` | Live audio channel |
| `GET` | `/interviews/{id}/feedback` | Fetch feedback report |

Full Swagger docs available at `http://localhost:8000/docs`.

---

## Docs

- [`docs/architecture.md`](docs/architecture.md) — system design, ADRs, technology choices
- [`docs/sprint-plan.md`](docs/sprint-plan.md) — 30-sprint implementation plan
