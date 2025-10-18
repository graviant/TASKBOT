# app/routers/start.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
import re

from ..services.allowed import AllowedUsers
from ..keyboards.reply import user_menu, admin_menu, claim_menu
from ..config import load_config
from ..fsm.task_creation import ClaimTask

router = Router(name="start")

def _main_menu_for(user_id: int):
    cfg = load_config()
    return admin_menu() if user_id in cfg.admins else user_menu()

# --- 1) /start с диплинком ---
@router.message(CommandStart(deep_link=True))
async def start_with_deeplink(
    message: Message,
    command: CommandObject,
    allowed: AllowedUsers,
    state: FSMContext,
):
    uid = message.from_user.id
    # TODO: здесь твоя проверка allowed / запись пользователя в БД

    arg = (command.args or "").strip()

    # ожидаем формат "assign_<id>"
    m = re.fullmatch(r"assign_(\d+)", arg)
    if m:
        assignment_id = int(m.group(1))

        # (опционально) проверка существования задания в БД:
        # exists = await repo.assignments.exists(assignment_id)
        # if not exists:
        #     await message.answer("Задание не найдено или недоступно.", reply_markup=_main_menu_for(uid))
        #     return

        await state.clear()
        await state.update_data(assignment_id=assignment_id)
        await state.set_state(ClaimTask.volume)
        await message.answer(
            f"Нашёл задание #{assignment_id}.\n"
            "Введите объём, который хотите взять (число, можно с запятой):",
            reply_markup=claim_menu(),
        )
        return

    # Нераспознанный диплинк → главное меню
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
    # TODO: здесь твоя проверка allowed / запись пользователя в БД

    await state.clear()
    await message.answer(
        "Добро пожаловать в TASKBOT!",
        reply_markup=_main_menu_for(uid),
    )
