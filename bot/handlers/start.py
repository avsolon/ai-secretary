import logging

from aiogram import types
from aiogram.filters import CommandStart

from bot.keyboards.inline import admin_menu_kb
from bot.keyboards.reply import main_reply_kb, admin_reply_kb
from db import crud

logger = logging.getLogger(__name__)


def register(dp, config, bot):
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        is_admin = message.from_user.id in config.ADMIN_IDS
        crud.create_user(
            config.DB_PATH,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            is_admin=is_admin,
        )

        welcome = (
            f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
            "Я — консультант магазина AKBNSK.RU. Помогу подобрать аккумулятор, "
            "расскажу о ценах и наличии.\n\n"
            "Просто напишите, что вас интересует, или используйте кнопки внизу."
        )
        if is_admin:
            welcome += "\n\n🔑 Панель администратора — нажмите кнопку внизу."
            await message.answer(welcome, reply_markup=admin_reply_kb())
        else:
            await message.answer(welcome, reply_markup=main_reply_kb())
