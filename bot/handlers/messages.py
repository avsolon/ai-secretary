import asyncio
import logging

from aiogram import types
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import cancel_kb, escalate_kb, services_kb
from bot.keyboards.reply import main_reply_kb, admin_reply_kb, admin_panel_reply_kb, remove_kb
from db import crud
from models.session import BookingSession

logger = logging.getLogger(__name__)

BOTTOM_KB = None


async def _keep_typing(bot, chat_id: int):
    for _ in range(5):
        await asyncio.sleep(4)
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            break


def register(dp, rag, config, bot):
    @dp.message()
    async def handle_message(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        text = message.text.strip()
        logger.info("Message from %d: %s", user_id, text[:100])

        is_admin = user_id in config.ADMIN_IDS

        crud.create_user(
            config.DB_PATH,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            is_admin=is_admin,
        )

        # Determine bottom keyboard
        bottom_kb = admin_reply_kb() if is_admin else main_reply_kb()

        # Show typing indicator
        await bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
        asyncio.create_task(_keep_typing(bot, user_id))

        # Handle bottom menu buttons
        if text == "🔍 Подобрать аккумулятор":
            await message.answer(
                "Напишите, какой аккумулятор вам нужен. Например:\n"
                "• «60 ампер обратная»\n"
                "• «аккумулятор для легковушки до 5000»\n"
                "• «BOSCH 70 ач»",
                reply_markup=bottom_kb,
            )
            return

        if text == "📞 Контакты":
            answer = rag.answer("какие контакты магазина")
            await message.answer(answer, reply_markup=bottom_kb)
            return

        if text == "❓ Часто задаваемые вопросы":
            await message.answer(
                "Я могу помочь:\n"
                "• Подобрать аккумулятор по параметрам\n"
                "• Рассказать о ценах и наличии\n"
                "• Показать контакты магазина\n\n"
                "Просто напишите ваш вопрос!",
                reply_markup=bottom_kb,
            )
            return

        if text == "🔑 Админ панель" and is_admin:
            await message.answer(
                "🔑 Панель администратора",
                reply_markup=admin_panel_reply_kb(),
            )
            return

        if text == "◀️ Назад в главное меню" and is_admin:
            await message.answer("Главное меню", reply_markup=bottom_kb)
            return

        # Admin panel actions
        if text == "📄 Загрузить документ" and is_admin:
            await message.answer("Отправьте файл PDF, DOCX или TXT для загрузки в базу знаний.", reply_markup=admin_panel_reply_kb())
            return

        if text == "📚 Список документов" and is_admin:
            docs = crud.get_documents(config.DB_PATH)
            if docs:
                reply = "📚 Документы в базе знаний:\n\n" + "\n".join(f"• {d['filename']} — {d['chunks_count']} фрагментов" for d in docs)
            else:
                reply = "📚 В базе знаний пока нет документов."
            await message.answer(reply, reply_markup=admin_panel_reply_kb())
            return

        if text == "🔄 Перестроить индекс" and is_admin:
            await message.answer("🔄 Функция перестроения индекса запускается через админ-панель в Telegram. Пока что индекс создаётся автоматически при загрузке документов.", reply_markup=admin_panel_reply_kb())
            return

        if text == "📅 Записи на сегодня" and is_admin:
            import datetime
            today = datetime.date.today().isoformat()
            apps = crud.get_appointments(config.DB_PATH, today)
            if apps:
                reply = f"📅 Записи на сегодня ({today}):\n\n" + "\n\n".join(
                    f"• {a['start_time']} - {a['end_time']}: {a['service_name']}\n  Клиент: {a.get('client_name', 'Не указан')}"
                    for a in apps
                )
            else:
                reply = f"📅 На сегодня ({today}) записей нет."
            await message.answer(reply, reply_markup=admin_panel_reply_kb())
            return

        if text == "⚙️ Управление услугами" and is_admin:
            services = crud.get_services(config.DB_PATH)
            if services:
                reply = "⚙️ Услуги:\n\n" + "\n".join(f"• {s['name']} ({s.get('duration_minutes',60)} мин)" for s in services)
            else:
                reply = "⚙️ Услуги пока не добавлены."
            await message.answer(reply, reply_markup=admin_panel_reply_kb())
            return

        data = await state.get_data()
        booking = BookingSession(**data.get("booking", {}))
        booking.user_id = user_id

        # Booking FSM
        if booking.state == "awaiting_service":
            booking.service = text
            booking.state = "awaiting_date"
            await state.update_data(booking=booking.__dict__)
            await message.answer(
                "На какую дату вы хотите записаться? (например: 25.12.2024 или завтра)",
                reply_markup=cancel_kb(),
            )
            return

        if booking.state == "awaiting_date":
            booking.date = text
            booking.state = "awaiting_time"
            await state.update_data(booking=booking.__dict__)
            await message.answer(
                "На какое время вам удобно? (например: 15:00)",
                reply_markup=cancel_kb(),
            )
            return

        if booking.state == "awaiting_name":
            booking.client_name = text
            booking.state = "awaiting_phone"
            await state.update_data(booking=booking.__dict__)
            await message.answer(
                "Ваш номер телефона для связи:",
                reply_markup=cancel_kb(),
            )
            return

        if booking.state == "awaiting_phone":
            booking.client_phone = text
            booking.state = "awaiting_comment"
            await state.update_data(booking=booking.__dict__)
            await message.answer(
                "Есть ли дополнительные пожелания? (можно пропустить, отправив прочерк -)",
                reply_markup=cancel_kb(),
            )
            return

        if booking.state == "awaiting_comment":
            if text != "-":
                booking.comment = text
            from bot.handlers.callback import finalize_booking
            await finalize_booking(message, state, booking, config, bot)
            return

        # Intent detection & RAG
        try:
            intent = rag.detect_intent(text)
        except Exception as e:
            logger.error("Intent detection failed: %s", e)
            intent = "question"

        logger.info("Detected intent: %s for user %d", intent, user_id)

        # Forbidden topics - short hardcoded response
        forbidden = ["политик", "религи", "секс", "поз", "трах", "любов", "отношени", "президент", "войн", "попа", "член"]
        if any(kw in text.lower() for kw in forbidden):
            await message.answer(
                "Мы продаём аккумуляторы. По этому вопросу ничем не помогу.",
                reply_markup=bottom_kb,
            )
            return

        # Simple greeting - short response without products
        greetings = ["привет", "здравствуй", "здрасти", "хай", "hello", "hi", "добрый день", "доброе утро", "добрый вечер"]
        if text.lower().strip() in greetings or text.lower().strip().rstrip("!.,") in greetings:
            await message.answer(
                f"Здравствуйте! Чем могу помочь? Подскажите, какой аккумулятор вас интересует.",
                reply_markup=bottom_kb,
            )
            return

        if intent == "booking":
            services = crud.get_services(config.DB_PATH)
            if services:
                booking.state = "idle"
                await state.update_data(booking=booking.__dict__)
                await message.answer(
                    "Выберите услугу из списка:",
                    reply_markup=services_kb(services),
                )
            else:
                booking.state = "awaiting_service"
                await state.update_data(booking=booking.__dict__)
                await message.answer(
                    "Напишите название услуги, на которую хотите записаться:",
                    reply_markup=cancel_kb(),
                )
            return

        if intent == "escalate":
            contact_keywords = ["как связать", "как позвонить", "как написать", "контакт", "телефон", "email"]
            if any(kw in text.lower() for kw in contact_keywords):
                answer = rag.answer("какие контакты магазина")
                await message.answer(answer, reply_markup=bottom_kb)
            else:
                await message.answer(
                    "Хотите, чтобы я передал ваш вопрос менеджеру?",
                    reply_markup=escalate_kb(),
                )
            return

        try:
            answer = rag.answer(text)
        except Exception as e:
            logger.error("RAG answer generation failed: %s", e)
            answer = "Извините, произошла ошибка. Попробуйте ещё раз или напишите по-другому."

        await message.answer(answer, reply_markup=bottom_kb)
