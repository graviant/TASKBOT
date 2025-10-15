from __future__ import annotations
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from decimal import Decimal

def assignment_markup(assignment_id: int, deep_prefix: str) -> InlineKeyboardMarkup:
    """
    Кнопка, уводящая в личку бота по deep-link для работы с заданием.
    """
    url = f"https://t.me/{deep_prefix}?start=assign_{assignment_id}"
    kb = [[InlineKeyboardButton(text="🧩 Работа с заданием", url=url)]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

_HUMAN_WORKTYPE = {
    "design":  "Дизайн",
    "montage": "Монтаж",
    "shooting":"Съёмка",
}

async def publish_assignment(
    bot: Bot,
    chat_id: int,
    thread_id: int | None,
    assignment_id: int,
    work_type: str,                 # design | montage | shooting | ...
    project: str | None,
    customer: str | None,
    total_volume: Decimal,
    deadline_text: str,             # ожид.: "%d.%m.%Y %H:%M"
    comment: str | None,
    deep_prefix: str,
    author_name: str,               # НОВОЕ: "@username" или "ФИО"
    volume_label: str,              # НОВОЕ: "КОЛИЧЕСТВО КАРТОЧЕК/ОПЕРАТОРОВ/РОЛИКОВ"
):
    """
    Публикует сообщение о задании в общий чат в требуемом формате (HTML).
    """

    # Разделим срок на дату и время (ожидаем пробел между ними)
    parts = (deadline_text or "").split(" ", 1)
    deadline_date = parts[0] if parts and parts[0] else "—"
    deadline_time = parts[1] if len(parts) > 1 else "—"

    worktype_h = _HUMAN_WORKTYPE.get(work_type, work_type.capitalize())

    text_lines = [
        f"📌СОЗДАНО ЗАДАНИЕ - {assignment_id} !",
        "",
        f"<b>ВИД РАБОТЫ:</b> {worktype_h}",
        f"<b>ЗАКАЗЧИК:</b> {customer or '—'}",
        "",
        f"<b>📆СРОК ИСПОЛНЕНИЯ:</b> {deadline_date}",
        f"<b>⏰ВРЕМЯ ИСПОЛНЕНИЯ:</b> {deadline_time}",
        "",
        f"<b>АВТОР ЗАДАНИЯ:</b> {author_name}",
        "",
        f"<b>{volume_label}:</b> {total_volume}",
        "",
        f"<b>НАЗВАНИЕ ПРОЕКТА:</b> {project or '—'}",
    ]

    if comment:
        text_lines.extend(["", f"<b>📝КОММЕНТАРИИ:</b> {comment}"])

    text = "\n".join(text_lines)
    kb = assignment_markup(assignment_id, deep_prefix)

    # В main уже стоит DefaultBotProperties(parse_mode=HTML), но явно укажем на всякий случай
    msg = await bot.send_message(
        chat_id,
        text,
        message_thread_id=thread_id,
        reply_markup=kb,
        parse_mode="HTML"
    )
    return msg.chat.id, msg.message_id
