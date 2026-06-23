import logging
import os
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    def __init__(self, config):
        self.config = config
        self._model = None
        self._ollama_client = None

    def _load_sentence_transformer(self):
        if self._model is not None:
            return self._model
        from sentence_transformers import SentenceTransformer
        cache = os.environ.get("HF_HOME", "") or os.environ.get("SENTENCE_TRANSFORMERS_HOME", "")
        kwargs = {"cache_folder": cache} if cache else {}
        logger.info("Loading sentence-transformer model: %s (cache=%s)", self.config.EMBEDDING_MODEL, cache or "default")
        self._model = SentenceTransformer(self.config.EMBEDDING_MODEL, **kwargs)
        return self._model

    def _get_ollama_client(self):
        if self._ollama_client is not None:
            return self._ollama_client
        import httpx
        model = self.config.OLLAMA_EMBEDDING_MODEL or self.config.OLLAMA_MODEL
        self._ollama_client = OllamaEmbeddingClient(self.config.OLLAMA_BASE_URL, model)
        return self._ollama_client

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])

        if self.config.LLM_PROVIDER == "ollama":
            client = self._get_ollama_client()
            return client.encode(texts)

        model = self._load_sentence_transformer()
        return model.encode(texts, show_progress_bar=False)

    def encode_query(self, text: str) -> np.ndarray:
        if self.config.LLM_PROVIDER == "ollama":
            client = self._get_ollama_client()
            return client.encode([text])[0]

        model = self._load_sentence_transformer()
        return model.encode([text], show_progress_bar=False)[0]

    @property
    def dim(self) -> int:
        sample = self.encode(["test"])
        return sample.shape[1]


class OllamaEmbeddingClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def encode(self, texts: List[str]) -> np.ndarray:
        import httpx
        embeddings = []
        for text in texts:
            resp = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings.append(data["embedding"])
        return np.array(embeddings, dtype=np.float32)
