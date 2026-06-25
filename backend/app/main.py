import time
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

import app.core.logger  # noqa: F401 — side-effect: configures logging on import
from app.api.interviews import router as interviews_router
from app.api.resumes import router as resumes_router
from app.cache.client import close_pool, get_redis, init_pool
from app.ws.gateway import router as ws_router
from app.core.config import settings
from app.core.logger import logger


def _run_migrations() -> None:
    cfg = AlembicConfig("alembic.ini")
    alembic_command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — running migrations")
    _run_migrations()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Initialising Redis pool at {}", settings.REDIS_URL)
    init_pool(settings.REDIS_URL)
    logger.info("Startup complete")
    yield
    logger.info("Shutting down — closing Redis pool")
    await close_pool()
    logger.info("Shutdown complete")


app = FastAPI(title="AI Interview Simulator", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes_router)
app.include_router(interviews_router)
app.include_router(ws_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("{} {} → {} ({:.1f}ms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.get("/health", tags=["meta"])
async def health(redis: Redis = Depends(get_redis)):
    try:
        await redis.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "error"
    return {"status": "ok", "redis": redis_status}
