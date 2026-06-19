import logging
import os
from pathlib import Path

from aiogram import types, F
from aiogram.filters import Command

from bot.keyboards.inline import admin_menu_kb
from db import crud
from utils.helpers import extract_text_from_file

logger = logging.getLogger(__name__)


def register(dp, rag, config, bot):
    @dp.message(Command("admin"))
    async def cmd_admin(message: types.Message):
        is_admin = crud.is_admin(config.DB_PATH, message.from_user.id)
        if not is_admin:
            await message.answer("⛔ У вас нет доступа к панели администратора.")
            return
        await message.answer(
            "🔑 Панель администратора\n\n"
            "Отправьте документ (PDF, DOCX, TXT) для загрузки в базу знаний "
            "или выберите действие:",
            reply_markup=admin_menu_kb(),
        )

    @dp.message(F.document)
    async def handle_document(message: types.Document):
        is_admin = crud.is_admin(config.DB_PATH, message.from_user.id)
        if not is_admin:
            await message.answer("⛔ У вас нет доступа.")
            return

        doc = message.document
        if doc.file_name and doc.file_name.endswith((".txt", ".pdf", ".docx")):
            status_msg = await message.answer("⏳ Загружаю документ...")
            file_path = Path(config.KNOWLEDGE_DIR) / doc.file_name
            file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                file_info = await bot.get_file(doc.file_id)
                await bot.download_file(file_info.file_path, destination=str(file_path))
                text = extract_text_from_file(str(file_path))
                if text.strip():
                    rag.add_document(text, source=doc.file_name)
                    chunks_count = len(text) // 500 + 1
                    crud.save_document_record(
                        config.DB_PATH,
                        filename=doc.file_name,
                        source=doc.file_name,
                        chunks_count=chunks_count,
                    )
                    await status_msg.edit_text(
                        f"✅ Документ \"{doc.file_name}\" загружен и обработан!\n"
                        f"📊 Создано фрагментов: {chunks_count}",
                        reply_markup=admin_menu_kb(),
                    )
                else:
                    await status_msg.edit_text(
                        "⚠️ Не удалось извлечь текст из документа.",
                        reply_markup=admin_menu_kb(),
                    )
            except Exception as e:
                logger.error("Failed to process document: %s", e)
                await status_msg.edit_text(
                    f"❌ Ошибка при обработке документа: {e}",
                    reply_markup=admin_menu_kb(),
                )
        else:
            await message.answer(
                "⚠️ Поддерживаются только форматы: TXT, PDF, DOCX.",
                reply_markup=admin_menu_kb(),
            )
