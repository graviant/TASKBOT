# app/middlewares/members.py
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from ..services.allowed import AllowedUsers


class AllMiddleware(BaseMiddleware):
    """
    Пропускает: админов, пользователей из кэша, а также /start (для первичной проверки).
    Никаких запросов к Telegram внутри мидлвари.
    """
    def __init__(self, admins: set[int], allowed_cache: AllowedUsers) -> None:
        super().__init__()
        self.admins = admins
        self.allowed = allowed_cache

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            # пропускаем все не Message апдейты (например CallbackQuery)
            return await handler(event, data)

        uid = event.from_user.id
        text = (event.text or "").strip() if event.text else ""

        # 1) админов всегда пропускаем
        if uid in self.admins:
            return await handler(event, data)

        # 2) /start всегда пропускаем (чтобы хэндлер мог добавить в БД и кэш)
        if text.startswith("/start"):
            return await handler(event, data)

        # 3) если пользователь уже в кэше allowed — пропускаем
        if await self.allowed.contains(uid):
            return await handler(event, data)

        # 4) иначе блокируем только в личке
        if event.chat.type == "private":
            await event.answer(
                "Доступ только для участников общего чата. "
                "Вступите в чат и повторно отправьте /start."
            )
        # в группах — молча игнорируем
        return

