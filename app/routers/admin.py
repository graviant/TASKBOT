from __future__ import annotations
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from ..middlewares.admin import AdminMiddleware
from ..db import repo

router = Router(name="admin")


@router.message(F.chat.type == "private", F.text == "🚮 Удалить любое задание")
async def admin_delete_prompt(message: Message):
    await message.answer("Введите команду вида: del &lt;assignment_id&gt;")


@router.message(F.chat.type == "private", F.text.regexp(r"^del\s+\d+$"))
async def admin_delete_do(message: Message):
    assignment_id = int(message.text.split()[1])
    ok = await repo.admin_delete_assignment(assignment_id)
    await message.answer("Удалено ✅" if ok else "Не найдено / уже закрыто.")


@router.message(F.chat.type == "private", F.text == "📦 Выгрузить БД")
async def export_db(message: Message):
    await message.answer("Используйте pg_dump на сервере БД (PostgreSQL).")


# --- новые команды для работы с темами ---

@router.message(Command("topic_id"))
async def topic_id(message: Message):
    """
    Показывает message_thread_id текущей темы (работает только в супергруппах с включёнными темами).
    """
    mid = message.message_thread_id
    if message.chat.type not in ("supergroup", "group") or not mid:
        return await message.answer("Эту команду нужно отправить прямо в конкретной теме (треде) супергруппы.")
    await message.answer(f"message_thread_id текущей темы: <code>{mid}</code>", parse_mode="HTML")


@router.message(Command("bind_worktype"))
async def bind_worktype(message: Message):
    """
    Привязка work_type → thread_id. Использовать в нужной теме.
    Пример: /bind_worktype design|montage|shooting
    """
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or parts[1] not in {"design", "montage", "shooting"}:
        return await message.answer("Формат: /bind_worktype design|montage|shooting")

    if message.chat.type not in ("supergroup", "group") or not message.message_thread_id:
        return await message.answer("Отправьте команду внутри нужной темы супергруппы.")

    work_type = parts[1]
    thread_id = message.message_thread_id
    await repo.upsert_thread_binding(work_type, thread_id)
    await message.answer(f"Привязал <b>{work_type}</b> к теме с id=<code>{thread_id}</code>", parse_mode="HTML")


@router.message(Command("show_threads"))
async def show_threads(message: Message):
    items = await repo.list_thread_bindings()
    print(items)
    if not items:
        return await message.answer("Привязок нет. Используйте /bind_worktype в нужных темах.")
    lines = [f"{it['work_type']}: <code>{it['thread_id']}</code>" for it in items]
    await message.answer("\n".join(lines), parse_mode="HTML")
