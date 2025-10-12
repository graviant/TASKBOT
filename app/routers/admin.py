from __future__ import annotations
from aiogram import Router, F
from aiogram.types import Message
from ..middlewares.admin import AdminMiddleware
from ..db import repo

router = Router(name="admin")


@router.message(F.chat.type == "private", F.text == "🚮 Удалить любое задание")
async def admin_delete_prompt(message: Message):
    await message.answer("Введите команду вида: del <assignment_id>")


@router.message(F.chat.type == "private", F.text.regexp(r"^del\s+\d+$"))
async def admin_delete_do(message: Message):
    assignment_id = int(message.text.split()[1])
    ok = await repo.admin_delete_assignment(assignment_id)
    await message.answer("Удалено ✅" if ok else "Не найдено / уже закрыто.")


@router.message(F.chat.type == "private", F.text == "📦 Выгрузить БД")
async def export_db(message: Message):
    await message.answer("Используйте pg_dump на сервере БД (PostgreSQL).")
