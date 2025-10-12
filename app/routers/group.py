from aiogram import Router, F
from aiogram.types import Message

router = Router(name="group")

@router.message(F.chat.type.in_({"group", "supergroup"}), F.new_chat_members)
async def bot_added_to_group(message: Message):
    """Реагируем, когда бота добавляют в чат"""
    for user in message.new_chat_members:
        if user.id == message.bot.id:
            await message.reply("👋 Всем привет! Я бот для управления задачами.\nИспользуйте /start в личке.")

@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def log_group_messages(message: Message):
    """Пример — логировать текстовые сообщения в чате (пока ничего не делаем)"""
    # можно просто игнорировать или использовать для статистики
    pass
