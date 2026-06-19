import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = field(default_factory=lambda: [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i])

    # LLM Provider: openai, gigachat, yandex, ollama
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gigachat")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # GigaChat
    GIGACHAT_CREDENTIALS: str = os.getenv("GIGACHAT_CREDENTIALS", "")
    GIGACHAT_SCOPE: str = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

    # YandexGPT
    YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY", "")
    YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "")

    # Embedding
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    # FAISS
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "data/faiss_index")

    # Knowledge base
    KNOWLEDGE_DIR: str = os.getenv("KNOWLEDGE_DIR", "data/knowledge")

    # DB
    DB_PATH: str = os.getenv("DB_PATH", "data/bot.db")

    # Google Calendar
    GOOGLE_CALENDAR_CRED: str = os.getenv("GOOGLE_CALENDAR_CRED", "data/google_credentials.json")
    GOOGLE_CALENDAR_TOKEN: str = os.getenv("GOOGLE_CALENDAR_TOKEN", "data/google_token.json")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "data/bot.log")


config = Config()
