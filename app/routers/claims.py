# app/routers/claims.py
from __future__ import annotations
from decimal import Decimal

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state

from .user_tasks import _main_menu_for
from ..fsm.task_creation import ClaimTask
from ..filters.validators import IsPositiveInt
from ..db import repo
from ..keyboards.reply import claim_menu

router = Router(name="claims")

# Шаг ввода объёма (валидное число по фильтру IsPositiveInt
@router.message(ClaimTask.volume, IsPositiveInt())
async def claim_set_volume(message: types.Message, state: FSMContext):
    vol = int(message.text.strip())  # гарантирует IsPositiveInt()
    data = await state.get_data()
    assignment_id = int(data.get("assignment_id") or 0)
    if not assignment_id:
        await state.clear()
        await message.answer(
            "Не удалось определить задание. Начните заново:",
            reply_markup=_main_menu_for(message.from_user.id),
        )
        return

    new_id = await repo.take_claim(
        assignment_id=assignment_id,
        executor_id=message.from_user.id,
        volume=vol,
    )

    if new_id is None:
        free = await repo.assignment_free_volume(assignment_id)
        await message.answer(
            f"Нельзя взять {vol}. Доступно сейчас: {free}. "
            "Введите другое значение:",
            reply_markup=claim_menu(),
        )
        return

    # Успех → сбрасываем состояние и показываем главное меню
    await state.clear()
    await message.answer(
        f"Готово! Вы взяли {vol} по заданию #{assignment_id} ✅",
        reply_markup=_main_menu_for(message.from_user.id),
    )

# Отмена взятия объёма (при активной FSM)
@router.message(~StateFilter(default_state), F.text == "❌ Отменить взятие")
async def claim_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Операция отменена.",
        reply_markup=_main_menu_for(message.from_user.id),
    )

# Фолбэк: ввели не число на шаге ввода объёма
@router.message(ClaimTask.volume)
async def claim_volume_wrong(message: types.Message):
    await message.answer(
        "Не получилось распознать число.\n"
        "Введите объём (целое число от 1)",
        reply_markup=claim_menu(),
    )
