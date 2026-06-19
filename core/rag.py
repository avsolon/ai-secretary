import logging
from typing import List, Dict, Any, Optional

from core.llm import LLMClient
from core.vector_store import VectorStore
from core.embeddings import EmbeddingProvider
from utils.helpers import chunk_text

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — ИИ-секретарь компании. Твоя задача — помогать клиентам, отвечая на их вопросы на основе базы знаний компании.

Правила:
1. Отвечай только на основе предоставленного контекста из базы знаний.
2. Если в контексте нет информации для ответа, вежливо скажи, что не знаешь ответа, и предложи связаться с менеджером.
3. Если клиент хочет записаться на услугу, помоги ему выбрать услугу и время.
4. Отвечай вежливо, профессионально, на том же языке, что и вопрос клиента.
5. В конце ответа укажи источники (названия документов), если они есть.
6. Не придумывай факты — используй только то, что есть в контексте."""


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

        answer_text = self.llm.generate(
            prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
        )

        if sources:
            sources_str = "\n\n📚 Источники:\n" + "\n".join(f"• {s}" for s in sources)
            answer_text += sources_str

        return answer_text

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
