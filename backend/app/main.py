import time
from contextlib import asynccontextmanager

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import Depends, FastAPI, Request
from redis.asyncio import Redis

import app.core.logger  # noqa: F401 — side-effect: configures logging on import
from app.cache.client import close_pool, get_redis, init_pool
from app.core.config import settings
from app.core.logger import logger


def _run_migrations() -> None:
    cfg = AlembicConfig("alembic.ini")
    alembic_command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — running migrations")
    _run_migrations()
    logger.info("Initialising Redis pool at {}", settings.REDIS_URL)
    init_pool(settings.REDIS_URL)
    logger.info("Startup complete")
    yield
    logger.info("Shutting down — closing Redis pool")
    await close_pool()
    logger.info("Shutdown complete")


app = FastAPI(title="AI Interview Simulator", version="0.1.0", lifespan=lifespan)


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
