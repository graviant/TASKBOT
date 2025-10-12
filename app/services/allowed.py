from __future__ import annotations
import asyncio


class AllowedUsers:
    """
    Памятка пользователей, которым разрешён доступ (is_member=true в БД).
    """

    def __init__(self) -> None:
        self._ids: set[int] = set()
        self._lock = asyncio.Lock()

    async def load(self, ids: list[int]) -> None:
        async with self._lock:
            self._ids = set(ids)

    async def add(self, user_id: int) -> None:
        async with self._lock:
            self._ids.add(user_id)

    async def remove(self, user_id: int) -> None:
        async with self._lock:
            self._ids.discard(user_id)

    async def contains(self, user_id: int) -> bool:
        async with self._lock:
            return user_id in self._ids

    # только для отладки/метрик
    async def snapshot(self) -> set[int]:
        async with self._lock:
            return set(self._ids)
