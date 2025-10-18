# app/keyboards/inline.py
from aiogram.utils.keyboard import InlineKeyboardBuilder

def worktype_keyboard():
    b = InlineKeyboardBuilder()
    b.button(text="🎨 Дизайн",  callback_data="worktype:design")
    b.button(text="🔧 Монтаж",  callback_data="worktype:montage")
    b.button(text="📹 Съёмка",  callback_data="worktype:shooting")
    b.adjust(3)  # три в ряд
    return b.as_markup()

def customers_keyboard(customers: list[dict]):
    """
    customers: [{ "id": 1, "name": "..." }, ...]
    """
    b = InlineKeyboardBuilder()
    for c in customers:
        b.button(text=c["name"], callback_data=f"customer:{c['id']}")
    b.adjust(2)  # по две кнопки в ряд (можно 1/3 — как удобно)
    return b.as_markup()

def claim_start_keyboard(assignment_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Взять задание", callback_data=f"claim_start:{assignment_id}")
    return b.as_markup()
