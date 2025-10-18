from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def user_menu() -> ReplyKeyboardMarkup:
    # Основное меню: БЕЗ кнопки "Отмена задания"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Выдать задание")],
            [KeyboardButton(text="📤 Мои выданные задания"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="🗑 Удалить моё задание"), KeyboardButton(text="🗑 Удалить мою задачу")],
        ],
        resize_keyboard=True
    )

def admin_menu() -> ReplyKeyboardMarkup:
    base = user_menu().keyboard  # тут уже нет "Отмена задания"
    admin_extra = [
        [KeyboardButton(text="👑 Назначить исполнителя"), KeyboardButton(text="♻️ Снять объём")],
        [KeyboardButton(text="🚮 Удалить любое задание"), KeyboardButton(text="📦 Выгрузить БД")],
    ]
    return ReplyKeyboardMarkup(keyboard=base + admin_extra, resize_keyboard=True)

def task_creation_menu() -> ReplyKeyboardMarkup:
    # Меню, показываемое ТОЛЬКО во время ввода задания
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена задания")]],
        resize_keyboard=True,
        selective=True,
        one_time_keyboard=False
    )

# ↓↓↓ НОВОЕ - claim_menu ↓↓↓
def claim_menu() -> ReplyKeyboardMarkup:
    # Меню, показываемое ТОЛЬКО во время взятия задания (отклик на объём)
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить взятие")]],
        resize_keyboard=True,
        selective=True,
        one_time_keyboard=False
    )

def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
