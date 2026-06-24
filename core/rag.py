import logging
from typing import List, Dict, Any, Optional

from core.llm import LLMClient
from core.vector_store import VectorStore
from core.embeddings import EmbeddingProvider
from utils.helpers import chunk_text

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — профессиональный продавец-консультант интернет-магазина AKBNSK.RU (аккумуляторы для авто). Твоя задача — продать товар и помочь клиенту.

РОЛЬ И ТОН:
• Ты сотрудник компании, говори от лица магазина: "у нас в наличии", "у нас есть", "наши цены", "вы можете купить у нас".
• Обращайся к клиенту на "вы" (вежливо).
• Если клиент здоровается ("привет", "здравствуйте") — поприветствуй в ответ коротко и дружелюбно, в том же тоне, представься и предложи помощь.
• Будь приветливым, но не навязчивым. Как живой продавец в хорошем магазине.

ПРАВИЛА РАБОТЫ С КАТАЛОГОМ:
• Используй ТОЛЬКО информацию из контекста ниже. НИКОГДА не выдумывай товары, бренды, цены, характеристики.
• Если в контексте нет названия бренда или товара, который назвал клиент — значит его нет в наличии.
• НЕ упоминай "в контексте", "в базе знаний", "согласно каталогу". Просто говори по факту.
• Не добавляй "Источники:" и список файлов в конце ответа.
• Если клиент просит конкретный товар (бренд + модель) — проверь, есть ли он в контексте. Если нет — скажи "к сожалению, этого товара сейчас нет в наличии" и предложи аналоги.
• Подбирай товары под нужные клиенту параметры: ёмкость (Ач), полярность (прямая/обратная), тип клемм, цена.
• Если подходящих товаров несколько — перечисли их с ценами и предложи выбрать.

ЗАПРЕЩЕНО:
• Выдумывать названия товаров, брендов, цены, телефоны, email — ТОЛЬКО из контекста.
• Писать "У вас", "ваш товар" — говори "у нас", "наш каталог", "в нашем магазине".
• Писать "Источник:" или "📚 Источники:".
• Придумывать контакты, которых нет в контексте."""


class RAGPipeline:
    def __init__(self, config, vector_store: VectorStore, embedding_provider: EmbeddingProvider):
        self.config = config
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.llm = LLMClient(config)

    def answer(self, query: str, top_k: int = 5) -> str:
        chunks = self.vector_store.search(query, top_k)
        context_parts = []
        sources = set()
        for c in chunks:
            context_parts.append(c.get("text", ""))
            if c.get("source"):
                sources.add(c["source"])

        context = "\n\n---\n\n".join(context_parts) if context_parts else ""

        if context:
            user_prompt = f"""Контекст из базы знаний компании:
{context}

Вопрос клиента: {query}

Дай развернутый, полезный ответ на вопрос клиента, используя информацию из контекста."""
        else:
            user_prompt = f"""Вопрос клиента: {query}

У меня нет информации по этому вопросу в базе знаний. Вежливо сообщи клиенту, что ты не знаешь ответа, и предложи связаться с менеджером."""

        return self.llm.generate(
            prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        )

    def add_document(self, text: str, source: str, chunk_size: int = 512, overlap: int = 64):
        chunks = chunk_text(text, chunk_size, overlap)
        texts = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "text": chunk,
                "source": source,
                "chunk_index": i,
            })
        self.vector_store.add_documents(texts, metadatas)
        logger.info("Added document '%s': %d chunks", source, len(chunks))

    def detect_intent(self, query: str) -> str:
        prompt = f"""Определи намерение клиента по его сообщению. Ответь одним словом:
- "booking" — если клиент хочет записаться на услугу, забронировать время, записаться на прием
- "question" — если клиент задает вопрос о компании, услугах, ценах
- "escalate" — если клиент просит соединить с человеком, недоволен, или вопрос сложный
- "other" — если не подходит ни под одну категорию

Сообщение клиента: {query}

Намерение:"""
        result = self.llm.generate(prompt=prompt, temperature=0.1).strip().lower()
        for intent in ["booking", "question", "escalate", "other"]:
            if intent in result:
                return intent
        return "other"
