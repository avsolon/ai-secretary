import logging

from aiogram import types
from aiogram.filters import CommandStart

from bot.keyboards.inline import main_menu_kb, admin_menu_kb
from db import crud

logger = logging.getLogger(__name__)


def register(dp, config, bot):
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        user = crud.create_user(
            config.DB_PATH,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        is_admin = crud.is_admin(config.DB_PATH, message.from_user.id)
        welcome = (
            f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
            "Я — ИИ-секретарь компании. Я могу:\n"
            "• Отвечать на вопросы о компании и услугах\n"
            "• Записывать вас на приём\n"
            "• Передавать сложные вопросы менеджеру\n\n"
            "Напишите свой вопрос или выберите действие ниже."
        )
        if is_admin:
            welcome += "\n\n🔑 Вы авторизованы как администратор."
            await message.answer(welcome, reply_markup=admin_menu_kb())
        else:
            await message.answer(welcome, reply_markup=main_menu_kb())
