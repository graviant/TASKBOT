# filters/validators.py
from aiogram.filters import BaseFilter
from aiogram.types import Message
from decimal import Decimal
from datetime import datetime
import re


class IsDecimal(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        try:
            Decimal(str(message.text).replace(",", "."))
            return True
        except Exception:
            return False


class IsDate(BaseFilter):
    def __init__(self, formats: tuple[str, ...] = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y")):
        self.formats = formats

    async def __call__(self, message: Message) -> bool:
        text = (message.text or "").strip()
        for fmt in self.formats:
            try:
                datetime.strptime(text, fmt)
                return True
            except ValueError:
                continue
        return False


class IsPositiveInt(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        t = message.text.strip()
        return bool(re.fullmatch(r"\d+", t)) and int(t) > 0