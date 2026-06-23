import logging

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from bot.keyboards.inline import main_menu_kb, cancel_kb, escalate_kb
from db import crud
from models.session import BookingSession

logger = logging.getLogger(__name__)


def register(dp, rag, config, bot):
    @dp.message()
    async def handle_message(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        text = message.text.strip()
        logger.info("Message from %d: %s", user_id, text[:100])

        crud.create_user(
            config.DB_PATH,
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        data = await state.get_data()
        booking = BookingSession(**data.get("booking", {}))
        booking.user_id = user_id

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

        try:
            intent = rag.detect_intent(text)
        except Exception as e:
            logger.error("Intent detection failed: %s", e)
            intent = "question"

        logger.info("Detected intent: %s for user %d", intent, user_id)

        if intent == "booking":
            services = crud.get_services(config.DB_PATH)
            if services:
                from bot.keyboards.inline import services_kb
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
            await message.answer(
                "Хотите, чтобы я передал ваш вопрос менеджеру?",
                reply_markup=escalate_kb(),
            )
            return

        try:
            answer = rag.answer(text)
        except Exception as e:
            logger.error("RAG answer generation failed: %s", e)
            answer = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже или свяжитесь с менеджером."

        await message.answer(answer, reply_markup=main_menu_kb())
