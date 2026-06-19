import logging
import os
import pickle
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np

from core.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, config, embedding_provider: EmbeddingProvider):
        self.config = config
        self.embedding_provider = embedding_provider
        self.index: faiss.Index = None
        self.metadata: List[Dict[str, Any]] = []
        self.index_path = Path(config.FAISS_INDEX_PATH)
        self.index_path.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        index_file = self.index_path / "index.faiss"
        meta_file = self.index_path / "metadata.pkl"
        if index_file.exists() and meta_file.exists():
            self.index = faiss.read_index(str(index_file))
            with open(meta_file, "rb") as f:
                self.metadata = pickle.load(f)
            logger.info("Loaded existing FAISS index with %d documents", len(self.metadata))
        else:
            self.index = None
            self.metadata = []
            logger.info("No existing FAISS index found, will create from documents on demand")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        query_vec = self.embedding_provider.encode_query(query)
        distances, indices = self.index.search(np.array([query_vec], dtype=np.float32), top_k)
        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.metadata):
                meta = dict(self.metadata[idx])
                meta["score"] = float(distances[0][list(indices[0]).index(idx)])
                results.append(meta)
        return results

    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        embeddings = self.embedding_provider.encode(texts)
        dim = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.array(embeddings, dtype=np.float32))
        self.metadata.extend(metadatas)
        self._save()

    def remove_all(self):
        self.index = None
        self.metadata = []
        self._save()

    def _save(self):
        index_file = self.index_path / "index.faiss"
        meta_file = self.index_path / "metadata.pkl"
        if self.index is not None and self.index.ntotal > 0:
            faiss.write_index(self.index, str(index_file))
        else:
            if index_file.exists():
                index_file.unlink()
        with open(meta_file, "wb") as f:
            pickle.dump(self.metadata, f)
        logger.info("Saved FAISS index with %d documents", len(self.metadata))

    @property
    def document_count(self) -> int:
        if self.index is None:
            return 0
        return self.index.ntotal
