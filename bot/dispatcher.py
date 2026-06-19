from aiogram import Dispatcher

from bot.handlers import start, messages, admin, callback


def setup_dispatcher(dp: Dispatcher, rag, config, bot):
    start.register(dp, config, bot)
    admin.register(dp, rag, config, bot)
    messages.register(dp, rag, config, bot)
    callback.register(dp, rag, config, bot)
