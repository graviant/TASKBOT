# app/routers/start.py
from __future__ import annotations
import re
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext

from ..services.allowed import AllowedUsers
from ..keyboards.reply import user_menu, admin_menu, claim_menu
from ..config import load_config
from ..fsm.task_creation import ClaimTask
from ..db import repo

router = Router(name="start")


def _main_menu_for(user_id: int):
    cfg = load_config()
    return admin_menu() if user_id in cfg.admins else user_menu()


async def _is_member_of_chat(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def _ensure_registered(message: Message, allowed: AllowedUsers) -> bool:
    """
    Админ (из .env ADMINS) — всегда проходит.
    Обычный пользователь — регистрируем только если состоит в общем чате (из .env).
    """
    cfg = load_config()
    bot: Bot = message.bot
    uid = message.from_user.id

    # --- Админ: без проверки общего чата
    if uid in cfg.admins:
        await repo.upsert_user_full(
            user_id=uid,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_admin=True,
            is_member=True,
        )
        if hasattr(allowed, "add"):
            await allowed.add(uid)
        return True

    # --- Обычный пользователь: проверяем членство в единственном общем чате из env
    # В конфиге general_chat_ids: list[int]; берём первый (единственный).
    if not cfg.general_chat_ids:
        await message.answer("Сервис недоступен: не задан GENERAL_CHAT_IDS в конфиге.")
        return False

    general_chat_id = int(cfg.general_chat_ids[0])

    is_member = await _is_member_of_chat(bot, general_chat_id, uid)
    if not is_member:
        await message.answer(
            "Доступ только для участников общего чата.\n"
            "Вступите в общий чат и затем отправьте /start в личку."
        )
        return False

    # Состоит — регистрируем и кладём в кэш
    await repo.upsert_user_full(
        user_id=uid,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        is_admin=False,
        is_member=True,
    )
    if hasattr(allowed, "add"):
        await allowed.add(uid)
    return True


# --- 1) /start с диплинком ---
@router.message(CommandStart(deep_link=True))
async def start_with_deeplink(
    message: Message,
    command: CommandObject,
    allowed: AllowedUsers,
    state: FSMContext,
):
    uid = message.from_user.id
    if not await _ensure_registered(message, allowed):
        return

    arg = (command.args or "").strip()
    m = re.fullmatch(r"assign_(\d+)", arg)
    if m:
        assignment_id = int(m.group(1))
        await state.clear()
        await state.update_data(assignment_id=assignment_id)
        await state.set_state(ClaimTask.volume)
        await message.answer(
            f"Нашёл задание #{assignment_id}.\n"
            "Введите объём, который хотите взять (целое число от 1):",
            reply_markup=claim_menu(),
        )
        return

    await state.clear()
    await message.answer(
        "Привет! Я помогу с заданиями. Выберите действие:",
        reply_markup=_main_menu_for(uid),
    )


# --- 2) Обычный /start без диплинка ---
@router.message(CommandStart())
async def start_plain(
    message: Message,
    allowed: AllowedUsers,
    state: FSMContext,
):
    uid = message.from_user.id
    if not await _ensure_registered(message, allowed):
        return

    await state.clear()
    await message.answer(
        "Добро пожаловать в TASKBOT!",
        reply_markup=_main_menu_for(uid),
    )
