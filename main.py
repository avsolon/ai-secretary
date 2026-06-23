import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import config
from bot.dispatcher import setup_dispatcher
from db.database import init_db
from core.vector_store import VectorStore
from core.embeddings import EmbeddingProvider
from core.rag import RAGPipeline
from utils.logger import setup_logger


async def main():
    setup_logger(config.LOG_LEVEL, config.LOG_FILE)
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Secretary Bot...")

    init_db(config.DB_PATH)
    logger.info("Database initialized")

    embedding_provider = EmbeddingProvider(config)
    logger.info("Embedding provider initialized")

    vector_store = VectorStore(config, embedding_provider)
    await vector_store.initialize()
    logger.info("Vector store initialized")

    rag = RAGPipeline(config, vector_store, embedding_provider)
    logger.info("RAG pipeline initialized")

    session = AiohttpSession(proxy=config.TG_PROXY) if config.TG_PROXY else None
    bot = Bot(
        token=config.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    setup_dispatcher(dp, rag, config, bot)

    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
