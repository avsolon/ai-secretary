from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Записаться на услугу", callback_data="booking_start")
    builder.button(text="📞 Связаться с менеджером", callback_data="escalate")
    builder.button(text="❓ Часто задаваемые вопросы", callback_data="faq")
    builder.adjust(1)
    return builder.as_markup()


def services_kb(services: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in services:
        name = s.get("name", "Услуга")
        builder.button(
            text=f"{name} ({s.get('duration_minutes', 60)} мин)",
            callback_data=f"service_{s['id']}",
        )
    builder.button(text="◀️ Назад", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def time_slots_kb(slots: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(
            text=f"{slot['start']} - {slot['end']}",
            callback_data=f"time_{slot['start']}_{slot['end']}",
        )
    builder.button(text="◀️ Другая дата", callback_data="booking_date")
    builder.button(text="◀️ Назад", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


def dates_kb(dates: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in dates:
        builder.button(text=d["label"], callback_data=f"date_{d['value']}")
    builder.button(text="◀️ Назад", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="booking_confirm")
    builder.button(text="❌ Отменить", callback_data="booking_cancel")
    builder.adjust(2)
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Загрузить документ", callback_data="admin_upload")
    builder.button(text="📚 Список документов", callback_data="admin_docs")
    builder.button(text="🔄 Перестроить индекс", callback_data="admin_reindex")
    builder.button(text="📅 Записи на сегодня", callback_data="admin_appointments")
    builder.button(text="⚙️ Управление услугами", callback_data="admin_services")
    builder.button(text="◀️ Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_services_kb(services: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(
            text=f"✏️ {s['name']} ({s.get('duration_minutes', 60)} мин)",
            callback_data=f"admin_edit_service_{s['id']}",
        )
    builder.button(text="➕ Добавить услугу", callback_data="admin_add_service")
    builder.button(text="◀️ Назад в админку", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Отмена", callback_data="booking_cancel")
    return builder.as_markup()


def escalate_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, свяжите с менеджером", callback_data="escalate_yes")
    builder.button(text="◀️ Нет, остаться с ботом", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()
