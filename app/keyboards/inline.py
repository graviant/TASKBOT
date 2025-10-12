from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def take_part_kb(assignment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Взять часть объёма", callback_data=f"take:{assignment_id}")
    ]])

def worktype_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎨 Дизайн", callback_data="worktype:design"),
                InlineKeyboardButton(text="🔧 Монтаж", callback_data="worktype:montage"),
                InlineKeyboardButton(text="📹 Съёмка", callback_data="worktype:shooting"),
            ]
        ]
    )

def customers_keyboard(customers: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for c in customers:
        kb.add(InlineKeyboardButton(text=c["name"], callback_data=f"customer:{c['id']}"))
    return kb