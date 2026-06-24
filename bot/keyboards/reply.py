from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_reply_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 Подобрать аккумулятор")
    builder.button(text="📞 Контакты")
    builder.button(text="❓ Часто задаваемые вопросы")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Напишите вопрос...")


def admin_reply_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 Подобрать аккумулятор")
    builder.button(text="📞 Контакты")
    builder.button(text="❓ Часто задаваемые вопросы")
    builder.button(text="🔑 Админ панель")
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Напишите вопрос...")


def admin_panel_reply_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📄 Загрузить документ")
    builder.button(text="📚 Список документов")
    builder.button(text="🔄 Перестроить индекс")
    builder.button(text="📅 Записи на сегодня")
    builder.button(text="⚙️ Управление услугами")
    builder.button(text="◀️ Назад в главное меню")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите действие...")


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
