# admin.py
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import Message


class AdminMiddleware(BaseMiddleware):
    def __init__(self, admins: set[int]) -> None:
        self.admins = admins
        super().__init__()

    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message, data: Dict[str, Any]) -> Any:
        if event.from_user and event.from_user.id in self.admins:
            return await handler(event, data)
        return
