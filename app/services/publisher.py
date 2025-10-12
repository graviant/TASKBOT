from __future__ import annotations
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from decimal import Decimal


def assignment_markup(assignment_id: int, deep_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🧩 Работа с заданием",
            url=f"https://t.me/{deep_prefix}?start={assignment_id}"
        )
    ]])


async def publish_assignment(
        bot: Bot,
        chat_id: int,
        thread_id: int | None,
        assignment_id: int,
        work_type: str,
        project: str | None,
        customer: str | None,
        total_volume: Decimal,
        deadline_text: str,
        comment: str | None,
        deep_prefix: str
):
    text = (
        f"🆕 *Задание #{assignment_id}*\n"
        f"Вид работ: *{work_type}*\n"
        f"Проект: {project or '—'} | Заказчик: {customer or '—'}\n"
        f"Объём: *{total_volume}*\n"
        f"Срок: {deadline_text}\n"
        f"{'Комментарий: ' + comment if comment else ''}"
    )
    kb = assignment_markup(assignment_id, deep_prefix)
    msg = await bot.send_message(chat_id, text, message_thread_id=thread_id, reply_markup=kb, parse_mode="Markdown")
    return msg.chat.id, msg.message_id
