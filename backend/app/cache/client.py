from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

_pool: ConnectionPool | None = None


def init_pool(url: str) -> None:
    global _pool
    _pool = ConnectionPool.from_url(url, decode_responses=True)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis(connection_pool=_pool)
    try:
        yield client
    finally:
        await client.aclose()
