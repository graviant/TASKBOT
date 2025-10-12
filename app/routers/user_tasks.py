from __future__ import annotations
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from decimal import Decimal
from datetime import datetime
from typing import Optional
from aiogram.types import CallbackQuery

from ..fsm.task_creation import TaskCreation
from ..filters.validators import IsDecimal
from ..db import repo
from ..services.publisher import publish_assignment
from ..config import load_config
from ..keyboards.reply import user_menu, admin_menu, task_creation_menu
from ..keyboards.inline import worktype_keyboard
from ..keyboards.inline import customers_keyboard  # функция, формирующая инлайн-кнопки из списка

router = Router(name="user_tasks")

# --- helpers ---

DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y")

def _parse_date(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def _main_menu_for(user_id: int):
    cfg = load_config()
    return admin_menu() if user_id in cfg.admins else user_menu()

# --- flow ---

@router.message(~StateFilter(default_state), F.chat.type == "private", F.text == "❌ Отмена задания")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание задания прервано.", reply_markup=_main_menu_for(message.from_user.id))

@router.message(StateFilter(default_state), F.chat.type == "private", F.text == "📝 Выдать задание")
async def start_task_creation(message: types.Message, state: FSMContext):
    await state.set_state(TaskCreation.work_type)
    await message.answer("Выберите вид задания:", reply_markup=worktype_keyboard())

# === выбор вида задания по кнопке ===
@router.callback_query(TaskCreation.work_type, F.data.startswith("worktype:"))
async def select_worktype(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]  # design / montage / shooting
    await state.update_data(work_type=value)
    await state.set_state(TaskCreation.deadline)

    await callback.message.edit_text(f"Вы выбрали: {value.capitalize()}")
    await callback.message.answer("Введите срок: YYYY-MM-DD, 31.12.2025", reply_markup=task_creation_menu())
    await callback.answer()

@router.message(TaskCreation.deadline, F.text)
async def ask_project(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    deadline = _parse_date(text)

    if deadline is None:
        await message.answer(
            "Не понял дату 😕\n"
            "Допустимые форматы: 2025-10-31, 31.10.2025, 31/10/2025.\n"
            "Пожалуйста, введите дату ещё раз:",
            reply_markup=task_creation_menu()
        )
        return
    await state.update_data(deadline=deadline)
    await state.set_state(TaskCreation.project)
    await message.answer("Введите проект:", reply_markup=task_creation_menu())


@router.message(TaskCreation.project, F.text)
async def ask_customer(message: types.Message, state: FSMContext):
    await state.update_data(project=message.text.strip())
    await state.set_state(TaskCreation.customer)
    customers = await repo.list_customers()
    await message.answer("Выберите заказчика:", reply_markup=customers_keyboard(customers))


@router.callback_query(TaskCreation.customer, F.data.startswith("customer:"))
async def select_customer(callback: CallbackQuery, state: FSMContext):
    customer_id = int(callback.data.split(":")[1])
    await state.update_data(customer_id=customer_id)  # сохраняем ID
    await state.set_state(TaskCreation.total_volume)
    name = await repo.get_customer_name(customer_id)
    await callback.message.edit_text(f"Вы выбрали заказчика: {name}")
    await callback.message.answer("Введите общий объём (число, можно с запятой):", reply_markup=task_creation_menu())
    await callback.answer()


@router.message(TaskCreation.customer, F.text)
async def ask_volume(message: types.Message, state: FSMContext):
    await state.update_data(customer=message.text.strip())
    await state.set_state(TaskCreation.total_volume)
    await message.answer("Введите общий объём (число, можно с запятой):", reply_markup=task_creation_menu())


@router.message(TaskCreation.total_volume, IsDecimal())
async def ask_comment(message: types.Message, state: FSMContext):
    vol = Decimal(message.text.replace(",", "."))
    if vol <= 0:
        await message.answer("Объём должен быть больше 0. Повторите ввод:", reply_markup=task_creation_menu())
        return
    await state.update_data(total_volume=vol)
    await state.set_state(TaskCreation.comment)
    await message.answer("Комментарий (или '-' если нет):", reply_markup=task_creation_menu())


@router.message(TaskCreation.comment, F.text)
async def finalize_task(message: types.Message, state: FSMContext):
    from ..keyboards.inline import customers_keyboard  # на случай, если понадобиться вернуть шаг выбора
    comment = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    cfg = load_config()

    # подстраховка: если по какой-то причине нет customer_id — вернём пользователя на шаг выбора
    customer_id = data.get("customer_id")
    if customer_id is None:
        customers = await repo.list_customers()
        await state.set_state(TaskCreation.customer)
        await message.answer("Похоже, вы не выбрали заказчика. Выберите заказчика:", reply_markup=customers_keyboard(customers))
        return

    # имя заказчика для публикации (а в БД сохраняем snapshot через INSERT)
    customer_name = await repo.get_customer_name(customer_id)

    # Создание задания (вставка с customer_id и snapshot внутри SQL)
    a_id = await repo.create_assignment(
        author_id=message.from_user.id,
        work_type=data["work_type"],
        deadline_at=data["deadline"],
        project=data["project"],
        customer_id=customer_id,                 # <<< ВАЖНО: передаём id, не строку
        total_volume=data["total_volume"],
        comment=comment
    )

    # Публикация
    thread_id = cfg.threads_by_worktype.get(data["work_type"])
    chat_id = cfg.general_chat_ids[0]
    deadline_text = data["deadline"].strftime("%Y-%m-%d") if data["deadline"] else "—"

    me = await message.bot.me()
    msg_chat_id, msg_id = await publish_assignment(
        bot=message.bot,
        chat_id=chat_id,
        thread_id=thread_id,
        assignment_id=a_id,
        work_type=data["work_type"],
        project=data["project"],
        customer=customer_name,                  # <<< для текста используем имя
        total_volume=data["total_volume"],
        deadline_text=deadline_text,
        comment=comment,
        deep_prefix=me.username
    )

    await repo.mark_assignment_published(a_id, msg_chat_id, msg_id)

    await state.clear()
    await message.answer("Задание опубликовано в общем чате ✅", reply_markup=_main_menu_for(message.from_user.id))


# --- прочие кнопки основного меню — только когда FSM НЕ активна ---

@router.message(StateFilter(default_state), F.chat.type == "private", F.text == "📤 Мои выданные задания")
async def my_assignments(message: types.Message):
    items = await repo.my_assignments(message.from_user.id)
    if not items:
        await message.answer("У вас нет выданных заданий.")
        return
    lines = [
        f"#{a['id']} {a['work_type']} | объём {a['total_volume']} | активное: {'да' if a['is_active'] else 'нет'}"
        for a in items[:20]
    ]
    await message.answer("\n".join(lines))

@router.message(StateFilter(default_state), F.chat.type == "private", F.text == "📋 Мои задачи")
async def my_tasks(message: types.Message):
    claims = await repo.my_open_claims(message.from_user.id)
    if not claims:
        await message.answer("У вас нет невыполненных задач.")
        return
    text = "\n".join([f"#{c['id']}: по заданию {c['assignment_id']}, объём {c['volume']}" for c in claims])
    await message.answer(text)

@router.message(StateFilter(default_state), F.chat.type == "private", F.text == "🗑 Удалить мою задачу")
async def delete_my_task_hint(message: types.Message):
    await message.answer("Отправьте ID вашей незакрытой задачи (число).")

@router.message(StateFilter(default_state), F.chat.type == "private", F.text.regexp(r"^\d+$"))
async def delete_my_task_do(message: types.Message):
    claim_id = int(message.text)
    ok = await repo.delete_my_open_claim(claim_id, message.from_user.id)
    await message.answer("Удалено ✅" if ok else "Не найдено / нет прав.")
