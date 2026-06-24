import datetime
import logging

from aiogram import types
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import (
    time_slots_kb,
    dates_kb,
    confirm_kb,
    main_menu_kb,
    services_kb,
    admin_menu_kb,
    admin_services_kb,
)
from core.calendar import GoogleCalendarClient
from db import crud
from models.session import BookingSession

logger = logging.getLogger(__name__)


def register(dp, rag, config, bot):
    @dp.callback_query()
    async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
        data = callback.data
        user_id = callback.from_user.id
        user_data = await state.get_data()
        booking = BookingSession(**user_data.get("booking", {}))
        booking.user_id = user_id

        if data == "main_menu":
            await state.clear()
            is_admin = crud.is_admin(config.DB_PATH, user_id)
            kb = admin_menu_kb() if is_admin else main_menu_kb()
            await callback.message.edit_text(
                "Чем я могу помочь?",
                reply_markup=kb,
            )
            await callback.answer()
            return

        if data == "booking_start":
            services = crud.get_services(config.DB_PATH)
            if services:
                await callback.message.edit_text(
                    "Выберите услугу:",
                    reply_markup=services_kb(services),
                )
            else:
                booking.state = "awaiting_service"
                await state.update_data(booking=booking.__dict__)
                await callback.message.edit_text(
                    "Напишите название услуги:"
                )
            await callback.answer()
            return

        if data.startswith("service_"):
            service_id = int(data.split("_")[1])
            services = crud.get_services(config.DB_PATH)
            service = next((s for s in services if s["id"] == service_id), None)
            if service:
                booking.service = service["name"]
                booking.temp_data["service_id"] = service["id"]
                booking.temp_data["duration"] = service.get("duration_minutes", 60)
            booking.state = "awaiting_date"
            await state.update_data(booking=booking.__dict__)
            await show_date_selection(callback, booking)
            await callback.answer()
            return

        if data == "booking_date":
            booking.state = "awaiting_date"
            await state.update_data(booking=booking.__dict__)
            await show_date_selection(callback, booking)
            await callback.answer()
            return

        if data.startswith("date_"):
            date_val = data.split("_", 1)[1]
            booking.date = date_val
            booking.state = "awaiting_time"
            await state.update_data(booking=booking.__dict__)

            calendar = GoogleCalendarClient(config)
            try:
                date_obj = datetime.date.fromisoformat(date_val)
            except ValueError:
                await callback.message.edit_text(
                    "Некорректная дата. Попробуйте снова."
                )
                await callback.answer()
                return

            try:
                work_start = "09:00"
                work_end = "18:00"
                duration = booking.temp_data.get("duration", 60)
                slots = calendar.get_free_slots(
                    date_obj, work_start, work_end, duration
                )
            except FileNotFoundError:
                slots = _generate_dummy_slots(work_start, work_end, duration)
            except Exception as e:
                logger.error("Calendar error: %s", e)
                slots = _generate_dummy_slots(work_start, work_end, duration)

            if slots:
                await callback.message.edit_text(
                    f"Доступное время на {date_val}:",
                    reply_markup=time_slots_kb(slots),
                )
            else:
                await callback.message.edit_text(
                    "На эту дату нет свободных слотов. Выберите другую дату.",
                    reply_markup=main_menu_kb(),
                )
            await callback.answer()
            return

        if data.startswith("time_"):
            parts = data.split("_")
            booking.start_iso = f"{booking.date}T{parts[1]}"
            booking.end_iso = f"{booking.date}T{parts[2]}"
            booking.state = "awaiting_name"
            await state.update_data(booking=booking.__dict__)
            await callback.message.edit_text(
                f"Отлично! {booking.service} на {booking.date} в {parts[1]}.\n\n"
                "Ваше имя:"
            )
            await callback.answer()
            return

        if data == "booking_confirm":
            await finalize_booking(callback.message, state, booking, config, bot)
            await callback.answer()
            return

        if data == "booking_cancel":
            await state.clear()
            await callback.message.edit_text(
                "Запись отменена. Если захотите записаться позже — обращайтесь!",
                reply_markup=main_menu_kb(),
            )
            await callback.answer()
            return

        if data == "escalate":
            from bot.keyboards.inline import escalate_kb
            await callback.message.edit_text(
                "Хотите, чтобы я передал ваш вопрос менеджеру?",
                reply_markup=escalate_kb(),
            )
            await callback.answer()
            return

        if data == "escalate_yes":
            await escalate_to_manager(callback, booking, config, bot)
            await callback.answer()
            return

        if data == "faq":
            await callback.message.edit_text(
                "Вы можете задать любой вопрос о нашей компании, "
                "и я постараюсь найти ответ в базе знаний. "
                "Просто напишите его в чат!",
                reply_markup=main_menu_kb(),
            )
            await callback.answer()
            return

        if data == "admin_menu":
            is_admin = crud.is_admin(config.DB_PATH, user_id)
            if is_admin:
                await callback.message.edit_text(
                    "🔑 Панель администратора",
                    reply_markup=admin_menu_kb(),
                )
            await callback.answer()
            return

        if data == "admin_upload":
            await callback.message.edit_text(
                "📄 Отправьте файл (PDF, DOCX, TXT) для загрузки в базу знаний.",
                reply_markup=admin_menu_kb(),
            )
            await callback.answer()
            return

        if data == "admin_docs":
            docs = crud.get_documents(config.DB_PATH)
            if docs:
                text = "📚 Документы в базе знаний:\n\n"
                for d in docs:
                    text += f"• {d['filename']} — {d['chunks_count']} фрагментов\n"
            else:
                text = "📚 В базе знаний пока нет документов."
            await callback.message.edit_text(text, reply_markup=admin_menu_kb())
            await callback.answer()
            return

        if data == "admin_reindex":
            await callback.message.edit_text(
                "🔄 Перестроение индекса... Это может занять некоторое время.",
                reply_markup=admin_menu_kb(),
            )
            await callback.answer()
            _reindex_knowledge_base(config, rag)
            await callback.message.answer(
                "✅ Индекс перестроен!",
                reply_markup=admin_menu_kb(),
            )
            return

        if data == "admin_appointments":
            today = datetime.date.today().isoformat()
            apps = crud.get_appointments(config.DB_PATH, today)
            if apps:
                text = f"📅 Записи на сегодня ({today}):\n\n"
                for a in apps:
                    text += f"• {a['start_time']} - {a['end_time']}: {a['service_name']}\n"
                    text += f"  Клиент: {a.get('client_name', 'Не указан')}\n\n"
            else:
                text = f"📅 На сегодня ({today}) записей нет."
            await callback.message.edit_text(text, reply_markup=admin_menu_kb())
            await callback.answer()
            return

        if data == "admin_services":
            services = crud.get_services(config.DB_PATH)
            await callback.message.edit_text(
                "⚙️ Управление услугами:",
                reply_markup=admin_services_kb(services),
            )
            await callback.answer()
            return

        if data == "admin_add_service":
            from aiogram import F
            await callback.message.edit_text(
                "Напишите название новой услуги в формате:\n"
                "Название | Описание | Длительность (мин)\n\n"
                "Например:\n"
                "Консультация | Первичная консультация | 60",
            )

            @dp.message(F.text)
            async def add_service_handler(msg: types.Message):
                parts = msg.text.split("|")
                name = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                duration = int(parts[2].strip()) if len(parts) > 2 else 60
                crud.add_service(config.DB_PATH, name, desc, duration)
                await msg.answer(
                    f"✅ Услуга \"{name}\" добавлена!",
                    reply_markup=admin_menu_kb(),
                )
                dp.message.unregister(add_service_handler)

            await callback.answer()
            return

        if data.startswith("admin_edit_service_"):
            service_id = int(data.split("_")[-1])
            services = crud.get_services(config.DB_PATH)
            service = next((s for s in services if s["id"] == service_id), None)
            if service:
                await callback.message.edit_text(
                    f"✏️ Редактирование: {service['name']}\n"
                    f"Описание: {service.get('description', '')}\n"
                    f"Длительность: {service.get('duration_minutes', 60)} мин\n\n"
                    "Функция редактирования будет доступна в следующей версии.",
                    reply_markup=admin_services_kb(services),
                )
            await callback.answer()
            return

        await callback.answer("Неизвестная команда")


async def show_date_selection(callback: types.CallbackQuery, booking: BookingSession):
    today = datetime.date.today()
    dates = []
    for i in range(7):
        d = today + datetime.timedelta(days=i)
        label = d.strftime("%a, %d.%m")
        dates.append({"label": label, "value": d.isoformat()})
    await callback.message.edit_text(
        f"Вы выбрали: {booking.service}\n\nВыберите удобную дату:",
        reply_markup=dates_kb(dates),
    )


async def finalize_booking(message: types.Message, state: FSMContext,
                           booking: BookingSession, config, bot):
    try:
        calendar = GoogleCalendarClient(config)
        start_dt = datetime.datetime.fromisoformat(booking.start_iso)
        end_dt = datetime.datetime.fromisoformat(booking.end_iso)
        summary = f"Запись: {booking.service}"
        desc = f"Клиент: {booking.client_name or 'Не указан'}\n"
        desc += f"Телефон: {booking.client_phone or 'Не указан'}\n"
        if booking.comment:
            desc += f"Комментарий: {booking.comment}\n"
        event = calendar.create_event(summary, start_dt, end_dt, desc)
        google_event_id = event.get("id") if event else None
    except FileNotFoundError as e:
        logger.warning("Calendar not configured: %s", e)
        google_event_id = None
    except Exception as e:
        logger.error("Calendar error: %s", e)
        google_event_id = None

    db_user = crud.get_user(config.DB_PATH, booking.user_id)
    user_db_id = db_user["id"] if db_user else 0
    crud.create_appointment(
        config.DB_PATH,
        user_id=user_db_id,
        service_name=booking.service or "Услуга",
        appointment_date=booking.date or "",
        start_time=booking.start_iso or "",
        end_time=booking.end_iso or "",
        client_name=booking.client_name,
        client_phone=booking.client_phone,
        comment=booking.comment,
        google_event_id=google_event_id,
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Вы записаны!</b>\n\n"
        f"📋 Услуга: {booking.service}\n"
        f"📅 Дата: {booking.date}\n"
        f"⏰ Время: {booking.start_iso.split('T')[1] if booking.start_iso else ''} - {booking.end_iso.split('T')[1] if booking.end_iso else ''}\n"
        f"👤 Имя: {booking.client_name or 'Не указано'}\n"
        f"📞 Телефон: {booking.client_phone or 'Не указан'}\n\n"
        "Если потребуется изменить или отменить запись — просто напишите мне!",
        reply_markup=main_menu_kb(),
    )

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📅 <b>Новая запись!</b>\n\n"
                f"📋 Услуга: {booking.service}\n"
                f"👤 Клиент: {booking.client_name or 'Не указан'}\n"
                f"📞 Телефон: {booking.client_phone or 'Не указан'}\n"
                f"📅 Дата: {booking.date}\n"
                f"⏰ Время: {booking.start_iso.split('T')[1] if booking.start_iso else ''}",
            )
        except Exception as e:
            logger.error("Failed to notify admin %d: %s", admin_id, e)


async def escalate_to_manager(callback: types.CallbackQuery, booking: BookingSession,
                               config, bot):
    await callback.message.edit_text(
        "Передаю ваш вопрос менеджеру. Ожидайте ответа в ближайшее время.",
        reply_markup=main_menu_kb(),
    )

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📞 <b>Запрос на связь с менеджером</b>\n\n"
                f"От: @{callback.from_user.username or callback.from_user.first_name}\n\n"
                f"Сообщение: {callback.message.text or '—'}",
            )
        except Exception as e:
            logger.error("Failed to escalate to admin %d: %s", admin_id, e)

    await callback.answer()


def _reindex_knowledge_base(config, rag):
    import os
    from utils.helpers import extract_text_from_file
    from pathlib import Path

    knowledge_dir = Path(config.KNOWLEDGE_DIR)
    if not knowledge_dir.exists():
        logger.warning("Knowledge directory does not exist: %s", knowledge_dir)
        return

    rag.vector_store.remove_all()
    for file_path in knowledge_dir.iterdir():
        if file_path.suffix.lower() in (".txt", ".pdf", ".docx"):
            try:
                text = extract_text_from_file(str(file_path))
                if text.strip():
                    rag.add_document(text, source=file_path.name)
                    crud.save_document_record(
                        config.DB_PATH,
                        filename=file_path.name,
                        source=file_path.name,
                        chunks_count=len(text) // 500 + 1,
                    )
                    logger.info("Re-indexed: %s", file_path.name)
            except Exception as e:
                logger.error("Failed to re-index %s: %s", file_path.name, e)


def _generate_dummy_slots(work_start: str, work_end: str, duration: int) -> list:
    import datetime
    start_h, start_m = map(int, work_start.split(":"))
    end_h, end_m = map(int, work_end.split(":"))
    current = datetime.time(start_h, start_m)
    end = datetime.time(end_h, end_m)
    slots = []
    while current.hour * 60 + current.minute + duration <= end.hour * 60 + end.minute:
        next_minutes = current.minute + duration
        next_h = current.hour + next_minutes // 60
        next_m = next_minutes % 60
        slots.append({
            "start": current.strftime("%H:%M"),
            "end": f"{next_h:02d}:{next_m:02d}",
        })
        current = datetime.time(next_h, next_m)
    return slots
