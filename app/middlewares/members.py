# members.py
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from ..services.allowed import AllowedUsers

class AllMiddleware(BaseMiddleware):
    """
    Пропускает: админов или пользователей из кэша AllowedUsers.
    Никаких запросов к Telegram внутри мидлвари.
    """
    def __init__(self, admins: set[int], allowed_cache: AllowedUsers) -> None:
        super().__init__()
        self.admins = admins
        self.allowed = allowed_cache

    async def __call__(self, handler: Callable, event: Message, data: Dict[str, Any]) -> Any:
        uid = event.from_user.id if event.from_user else None
        if uid in self.admins:
            return await handler(event, data)
        if uid and await self.allowed.contains(uid):
            return await handler(event, data)
        # нет прав — попросим /start (там первая проверка членства в чате)
        if event.chat.type == "private":
            await event.answer("Доступ только для участников общего чата. Нажмите /start для проверки.")
        # В группах молча игнорируем
        return
