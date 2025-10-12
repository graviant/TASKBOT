from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def take_part_kb(assignment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Взять часть объёма", callback_data=f"take:{assignment_id}")
    ]])
