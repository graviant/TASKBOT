from __future__ import annotations
from psycopg_pool import AsyncConnectionPool

_pool: AsyncConnectionPool | None = None


async def init_pool(dsn: str) -> AsyncConnectionPool:
    """
    Создаёт глобальный пул и явно ОТКРЫВАЕТ его.
    """
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=10,
            open=False,  # отложенное открытие
            kwargs={"autocommit": False}
        )
        await _pool.open()  # <-- обязательно await!
    return _pool


def get_pool() -> AsyncConnectionPool:
    assert _pool is not None, "Pool is not initialized"
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
