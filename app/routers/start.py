from __future__ import annotations
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from ..db import repo
from ..config import load_config
from ..keyboards.reply import user_menu, admin_menu
from ..services.allowed import AllowedUsers

router = Router(name="start")

@router.message(CommandStart())
async def start_cmd(message: Message, allowed: AllowedUsers):
    """
    1) Если пользователь уже в кэше — просто отдаем меню.
    2) Если не в кэше — один раз проверяем через Telegram membership в одном из общих чатов.
       Если состоит — пишем в БД is_member=true, добавляем в кэш.
    """
    cfg = load_config()
    uid = message.from_user.id

    # если уже известен — просто меню
    if (uid in cfg.admins) or (await allowed.contains(uid)):
        kb = admin_menu() if uid in cfg.admins else user_menu()
        await repo.upsert_user_full(
            user_id=uid,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_admin=uid in cfg.admins,
            is_member=True if uid not in cfg.admins else True  # для админов ставим true
        )
        await message.answer("Привет! Я помогу с заданиями. Выберите действие:", reply_markup=kb)
        return

    # первая проверка членства через Telegram
    is_member = False
    for chat_id in cfg.general_chat_ids:
        try:
            member = await message.bot.get_chat_member(chat_id, uid)
            if member.status in ("creator", "administrator", "member"):
                is_member = True
                break
        except Exception:
            continue

    if is_member or (uid in cfg.admins):
        # пишем в БД и в кэш
        await repo.upsert_user_full(
            user_id=uid,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_admin=uid in cfg.admins,
            is_member=True
        )
        await allowed.add(uid)
        kb = admin_menu() if uid in cfg.admins else user_menu()
        await message.answer("Привет! Доступ подтверждён. Выберите действие:", reply_markup=kb)
    else:
        await repo.upsert_user_full(
            user_id=uid,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_admin=False,
            is_member=False
        )
        await message.answer("Доступ только для участников общего чата. "
                             "Вступите в чат и повторно отправьте /start.")

