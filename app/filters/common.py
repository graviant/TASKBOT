from aiogram.filters import BaseFilter
from aiogram.types import Message


class IsPrivate(BaseFilter):
    """Сообщение только из лички с ботом"""

    async def __call__(self, message: Message) -> bool:
        return message.chat.type == "private"


class IsGroup(BaseFilter):
    """Сообщение только из группы/супергруппы"""

    async def __call__(self, message: Message) -> bool:
        return message.chat.type in ("group", "supergroup")
